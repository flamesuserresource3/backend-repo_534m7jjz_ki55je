const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

function calcDiscounted(price, discount) {
  return Math.round(price * (1 - (discount || 0) / 100));
}

exports.createOrder = async (req, res, next) => {
  try {
    const userId = req.user.id;
    const { items } = req.body; // [{ productId, quantity }]
    if (!Array.isArray(items) || items.length === 0) return res.status(400).json({ error: 'No items provided' });

    // Fetch products and validate
    const productIds = items.map(i => i.productId);
    const products = await prisma.product.findMany({ where: { id: { in: productIds } } });
    if (products.length !== items.length) return res.status(400).json({ error: 'Invalid products in order' });

    let total = 0;
    const orderItemsData = [];

    for (const item of items) {
      const p = products.find(pr => pr.id === item.productId);
      if (!p) return res.status(400).json({ error: 'Invalid product' });
      if (p.stock < item.quantity) return res.status(400).json({ error: `Insufficient stock for ${p.name}` });
      const unitPrice = calcDiscounted(p.price, p.discount);
      total += unitPrice * item.quantity;
      orderItemsData.push({ productId: p.id, quantity: item.quantity, unitPrice });
    }

    // Credit check
    const credit = await prisma.creditAccount.findUnique({ where: { userId } });
    if (!credit) return res.status(400).json({ error: 'Credit account not found' });
    if (credit.used + total > credit.limit) return res.status(402).json({ error: 'Credit limit exceeded' });

    // Create order in transaction
    const result = await prisma.$transaction(async (tx) => {
      const order = await tx.order.create({
        data: {
          userId,
          total,
          items: {
            create: orderItemsData,
          },
        },
        include: { items: true },
      });

      // Decrement stock
      for (const item of items) {
        await tx.product.update({
          where: { id: item.productId },
          data: { stock: { decrement: item.quantity } },
        });
      }

      // Update credit used
      await tx.creditAccount.update({ where: { userId }, data: { used: credit.used + total } });

      return order;
    });

    res.status(201).json({ order: result });
  } catch (err) {
    next(err);
  }
};

exports.listOrders = async (req, res, next) => {
  try {
    const userId = req.user.id;
    const orders = await prisma.order.findMany({ where: { userId }, include: { items: true }, orderBy: { createdAt: 'desc' } });
    res.json({ orders });
  } catch (err) {
    next(err);
  }
};

exports.getOrder = async (req, res, next) => {
  try {
    const userId = req.user.id;
    const id = parseInt(req.params.id, 10);
    const order = await prisma.order.findFirst({ where: { id, userId }, include: { items: true } });
    if (!order) return res.status(404).json({ error: 'Order not found' });
    res.json({ order });
  } catch (err) {
    next(err);
  }
};
