// HTML escape helper (issue #517)
function esc(s) {
  const d = document.createElement('div');
  d.textContent = String(s ?? '');
  return d.innerHTML;
}

// Retirement Simulator - Complete Working Code

let growthChart = null;

function formatCurrency(amount) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
    minimumFractionDigits: 0,
  }).format(amount);
}

function calculateFutureValue(monthlyInvestment, annualReturn, years) {
  if (monthlyInvestment <= 0 || annualReturn <= 0 || years <= 0) return 0;
  const monthlyRate = annualReturn / 100 / 12;
  const months = years * 12;
  if (monthlyRate === 0) return monthlyInvestment * months;
  return (
    monthlyInvestment *
    ((Math.pow(1 + monthlyRate, months) - 1) / monthlyRate) *
    (1 + monthlyRate)
  );
}

function calculateLumpsumValue(currentSavings, annualReturn, years) {
  if (currentSavings <= 0 || annualReturn <= 0 || years <= 0)
    return currentSavings;
  return currentSavings * Math.pow(1 + annualReturn / 100, years);
}

function adjustForInflation(nominalValue, inflationRate, years) {
  if (inflationRate <= 0 || years <= 0) return nominalValue;
  return nominalValue / Math.pow(1 + inflationRate / 100, years);
}

function generateYearlyData(
  currentAge,
  retirementAge,
  monthlyInvestment,
  currentSavings,
  returnRate,
  inflationRate,
) {
  const years = retirementAge - currentAge;
  const data = { years: [], nominalCorpus: [], realCorpus: [] };
  for (let year = 0; year <= years; year++) {
    data.years.push(currentAge + year);
    const fvFromSIP = calculateFutureValue(monthlyInvestment, returnRate, year);
    const fvFromLumpsum = calculateLumpsumValue(
      currentSavings,
      returnRate,
      year,
    );
    const totalNominal = fvFromSIP + fvFromLumpsum;
    data.nominalCorpus.push(totalNominal);
    data.realCorpus.push(adjustForInflation(totalNominal, inflationRate, year));
  }
  return data;
}

function updateChart(yearlyData) {
  const ctx = document.getElementById('growthChart').getContext('2d');
  if (growthChart) {
    growthChart.destroy();
  }
  growthChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: yearlyData.years,
      datasets: [
        {
          label: 'Nominal Corpus (Without Inflation)',
          data: yearlyData.nominalCorpus,
          borderColor: '#d4a843',
          backgroundColor: 'rgba(212, 168, 67, 0.1)',
          borderWidth: 3,
          fill: true,
          tension: 0.4,
          pointRadius: 3,
        },
        {
          label: 'Real Corpus (Inflation-Adjusted)',
          data: yearlyData.realCorpus,
          borderColor: '#14c8bf',
          backgroundColor: 'rgba(20, 200, 191, 0.1)',
          borderWidth: 3,
          fill: true,
          tension: 0.4,
          pointRadius: 3,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        tooltip: {
          callbacks: {
            label: function (context) {
              return context.dataset.label + ': ' + formatCurrency(context.raw);
            },
          },
        },
        legend: {
          position: 'top',
          labels: { color: '#eef0f5' },
        },
      },
      scales: {
        y: {
          ticks: {
            callback: function (value) {
              return formatCurrency(value);
            },
            color: '#5a6a82',
          },
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
        },
        x: {
          ticks: { color: '#5a6a82' },
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
        },
      },
    },
  });
}

function calculateRetirement() {
  const currentAge = parseInt(document.getElementById('currentAge').value);
  const retirementAge = parseInt(
    document.getElementById('retirementAge').value,
  );
  const currentSavings = parseFloat(
    document.getElementById('currentSavings').value,
  );
  const monthlyInvestment = parseFloat(
    document.getElementById('monthlyInvestment').value,
  );
  const returnRate = parseFloat(document.getElementById('returnRate').value);
  const inflationRate = parseFloat(
    document.getElementById('inflationRate').value,
  );

  if (currentAge >= retirementAge) {
    document.getElementById('insights').innerHTML = `
            <div class="alert alert-warning">❌ Retirement age must be greater than current age!</div>
        `;
    return;
  }

  const years = retirementAge - currentAge;
  const fvFromSIP = calculateFutureValue(monthlyInvestment, returnRate, years);
  const fvFromLumpsum = calculateLumpsumValue(
    currentSavings,
    returnRate,
    years,
  );
  const totalNominal = fvFromSIP + fvFromLumpsum;
  const totalReal = adjustForInflation(totalNominal, inflationRate, years);
  const purchasingPowerLoss = (
    ((totalNominal - totalReal) / totalNominal) *
    100
  ).toFixed(1);

  document.getElementById('nominalCorpus').innerHTML =
    formatCurrency(totalNominal);
  document.getElementById('realCorpus').innerHTML = formatCurrency(totalReal);

  const yearlyData = generateYearlyData(
    currentAge,
    retirementAge,
    monthlyInvestment,
    currentSavings,
    returnRate,
    inflationRate,
  );
  updateChart(yearlyData);

  document.getElementById('insights').innerHTML = `
        <div class="alert alert-success">
            <strong>📊 Key Finding:</strong><br>
            Your retirement corpus in today's value will be <strong>${formatCurrency(totalReal)}</strong>.
        </div>
        <div class="alert alert-warning">
            <strong>⚠️ Inflation Impact:</strong><br>
            Inflation will reduce purchasing power by <strong>${purchasingPowerLoss}%</strong>.
        </div>
        <div class="alert alert-info">
            <strong>💡 What this means:</strong><br>
            While your bank statement will show <strong>${formatCurrency(totalNominal)}</strong>, 
            you'll only be able to buy what <strong>${formatCurrency(totalReal)}</strong> buys today.
        </div>
    `;
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('retirementForm');
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      calculateRetirement();
    });
  }
  calculateRetirement();
});
