const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

// Users
exports.adminListUsers = async (_req, res, next) => {
  try {
    const users = await prisma.user.findMany({ include: { subscription: true, creditAccount: true } });
    res.json({ users: users.map(u => ({ ...u, passwordHash: undefined })) });
  } catch (err) {
    next(err);
  }
};

exports.adminUpdateUser = async (req, res, next) => {
  try {
    const id = parseInt(req.params.id, 10);
    const { name, isAdmin, status } = req.body; // status may affect subscription
    const data = {};
    if (typeof name === 'string') data.name = name;
    if (typeof isAdmin === 'boolean') data.isAdmin = isAdmin;

    const user = await prisma.user.update({ where: { id }, data });

    if (status) {
      await prisma.subscription.update({ where: { userId: id }, data: { status } });
    }

    const full = await prisma.user.findUnique({ where: { id }, include: { subscription: true, creditAccount: true } });
    res.json({ user: { ...full, passwordHash: undefined } });
  } catch (err) {
    next(err);
  }
};

// Products
exports.adminListProducts = async (_req, res, next) => {
  try {
    const products = await prisma.product.findMany({ orderBy: { createdAt: 'desc' } });
    res.json({ products });
  } catch (err) {
    next(err);
  }
};

exports.adminCreateProduct = async (req, res, next) => {
  try {
    const { name, description, price, discount, stock, imageUrl } = req.body;
    if (!name || typeof price !== 'number') return res.status(400).json({ error: 'Name and price are required' });
    const product = await prisma.product.create({ data: { name, description, price, discount: discount || 0, stock: stock || 0, imageUrl } });
    res.status(201).json({ product });
  } catch (err) {
    next(err);
  }
};

exports.adminUpdateProduct = async (req, res, next) => {
  try {
    const id = parseInt(req.params.id, 10);
    const { name, description, price, discount, stock, imageUrl } = req.body;
    const data = {};
    if (name !== undefined) data.name = name;
    if (description !== undefined) data.description = description;
    if (price !== undefined) data.price = price;
    if (discount !== undefined) data.discount = discount;
    if (stock !== undefined) data.stock = stock;
    if (imageUrl !== undefined) data.imageUrl = imageUrl;
    const product = await prisma.product.update({ where: { id }, data });
    res.json({ product });
  } catch (err) {
    next(err);
  }
};

exports.adminDeleteProduct = async (req, res, next) => {
  try {
    const id = parseInt(req.params.id, 10);
    await prisma.product.delete({ where: { id } });
    res.json({ success: true });
  } catch (err) {
    next(err);
  }
};

// Credits
exports.adminSetCredit = async (req, res, next) => {
  try {
    const id = parseInt(req.params.id, 10);
    const { limit, used, resetDay } = req.body;
    const account = await prisma.creditAccount.update({ where: { userId: id }, data: {
      ...(limit !== undefined ? { limit } : {}),
      ...(used !== undefined ? { used } : {}),
      ...(resetDay !== undefined ? { resetDay } : {}),
    }});
    res.json({ credit: { ...account, remaining: account.limit - account.used } });
  } catch (err) {
    next(err);
  }
};
