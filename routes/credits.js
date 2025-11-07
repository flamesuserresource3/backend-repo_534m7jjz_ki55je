const express = require('express');
const router = express.Router();
const { getCredit, requestIncrease, resetIfNeeded } = require('../controllers/creditController');
const { authRequired } = require('../utils/auth');

router.get('/', authRequired, resetIfNeeded, getCredit);
router.post('/request-increase', authRequired, requestIncrease);

module.exports = router;
