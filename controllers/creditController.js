const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

exports.resetIfNeeded = async (req, _res, next) => {
  try {
    const userId = req.user.id;
    const credit = await prisma.creditAccount.findUnique({ where: { userId } });
    if (!credit) return next();

    const now = new Date();
    const day = now.getDate();
    if (day === credit.resetDay) {
      await prisma.creditAccount.update({ where: { userId }, data: { used: 0 } });
    }
    next();
  } catch (err) {
    next(err);
  }
};

exports.getCredit = async (req, res, next) => {
  try {
    const userId = req.user.id;
    const credit = await prisma.creditAccount.findUnique({ where: { userId } });
    if (!credit) return res.status(404).json({ error: 'Credit account not found' });
    const remaining = credit.limit - credit.used;
    res.json({ credit: { ...credit, remaining } });
  } catch (err) {
    next(err);
  }
};

exports.requestIncrease = async (req, res, next) => {
  try {
    const userId = req.user.id;
    const { amount } = req.body;
    const increment = parseInt(amount, 10) || 0;
    if (increment <= 0) return res.status(400).json({ error: 'Invalid amount' });

    const credit = await prisma.creditAccount.findUnique({ where: { userId } });
    if (!credit) return res.status(404).json({ error: 'Credit account not found' });

    // For demo: auto-approve up to +2000
    const MAX_AUTO = 2000;
    const newLimit = credit.limit + Math.min(increment, MAX_AUTO);
    const updated = await prisma.creditAccount.update({ where: { userId }, data: { limit: newLimit } });
    res.json({ credit: { ...updated, remaining: updated.limit - updated.used } });
  } catch (err) {
    next(err);
  }
};
