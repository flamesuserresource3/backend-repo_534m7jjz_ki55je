const express = require('express');
const router = express.Router();
const { adminRequired } = require('../utils/auth');
const {
  adminListUsers,
  adminUpdateUser,
  adminListProducts,
  adminCreateProduct,
  adminUpdateProduct,
  adminDeleteProduct,
  adminSetCredit,
} = require('../controllers/adminController');

router.use(adminRequired);

// Users
router.get('/users', adminListUsers);
router.patch('/users/:id', adminUpdateUser);

// Products
router.get('/products', adminListProducts);
router.post('/products', adminCreateProduct);
router.patch('/products/:id', adminUpdateProduct);
router.delete('/products/:id', adminDeleteProduct);

// Credits
router.put('/users/:id/credit', adminSetCredit);

module.exports = router;
