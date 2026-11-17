// Indian-style currency formatting. Matches utils/formatting.py::format_inr.
(function (root) {
  var RUPEE = '₹';

  function toNumber(amount) {
    if (amount === null || amount === undefined || typeof amount === 'boolean') return 0;
    var n = typeof amount === 'number' ? amount : parseFloat(String(amount).replace(/,/g, ''));
    return isFinite(n) ? n : 0;
  }

  // formatINR(1234567.5) -> "₹12,34,567.50"; formatINR(1234567.5, { compact: true }) -> "₹12.3 L"
  function formatINR(amount, options) {
    options = options || {};
    var decimals = options.decimals === undefined ? 2 : options.decimals;
    var n = toNumber(amount);
    var sign = n < 0 ? '-' : '';
    n = Math.abs(n);

    if (options.compact && n >= 1e5) {
      var cr = n >= 1e7;
      var scaled = (cr ? n / 1e7 : n / 1e5).toFixed(1);
      if (!cr && parseFloat(scaled) >= 100) {
        cr = true;
        scaled = (n / 1e7).toFixed(1);
      }
      return sign + RUPEE + scaled + (cr ? ' Cr' : ' L');
    }

    var text = new Intl.NumberFormat('en-IN', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(n);
    if (parseFloat(text.replace(/,/g, '')) === 0) sign = '';
    return sign + RUPEE + text;
  }

  root.formatINR = formatINR;
})(window);
