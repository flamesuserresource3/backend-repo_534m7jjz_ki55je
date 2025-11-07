const express = require('express');
const router = express.Router();
const {
  listProducts,
  getProduct,
} = require('../controllers/productController');
const { authOptional } = require('../utils/auth');

router.get('/', authOptional, listProducts);
router.get('/:id', authOptional, getProduct);

module.exports = router;
