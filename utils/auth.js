const jwt = require('jsonwebtoken');
const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret';

async function attachUser(req, _res, next) {
  try {
    const auth = req.headers.authorization || '';
    const token = auth.startsWith('Bearer ') ? auth.slice(7) : null;
    if (!token) return next();
    const decoded = jwt.verify(token, JWT_SECRET);
    const user = await prisma.user.findUnique({ where: { id: decoded.sub } });
    if (user) req.user = { id: user.id, email: user.email, isAdmin: user.isAdmin };
    next();
  } catch (_err) {
    next();
  }
}

function authRequired(req, res, next) {
  attachUser(req, res, () => {
    if (!req.user) return res.status(401).json({ error: 'Unauthorized' });
    next();
  });
}

function authOptional(req, res, next) {
  attachUser(req, res, next);
}

function adminRequired(req, res, next) {
  attachUser(req, res, () => {
    if (!req.user) return res.status(401).json({ error: 'Unauthorized' });
    if (!req.user.isAdmin) return res.status(403).json({ error: 'Forbidden' });
    next();
  });
}

module.exports = { authRequired, authOptional, adminRequired };
