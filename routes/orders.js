const express = require('express');
const router = express.Router();
const { createOrder, listOrders, getOrder } = require('../controllers/orderController');
const { authRequired } = require('../utils/auth');

router.post('/', authRequired, createOrder);
router.get('/', authRequired, listOrders);
router.get('/:id', authRequired, getOrder);

module.exports = router;
