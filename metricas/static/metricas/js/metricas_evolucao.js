// Lê os dados reais do histórico (enviados pela view) e desenha os gráficos
const dadosGrafico = JSON.parse(document.getElementById('dados-grafico').textContent);

const eixo = { ticks: { color: '#8A939C' }, grid: { color: '#2A3138' } };
const opcoes = {
  plugins: { legend: { labels: { color: '#F2F0EC' } } },
  scales: { x: eixo, y: eixo },
};

function linha(id, label, dados, cor, fundo) {
  new Chart(document.getElementById(id), {
    type: 'line',
    data: {
      labels: dadosGrafico.labels,
      datasets: [{
        label, data: dados,
        borderColor: cor, backgroundColor: fundo,
        fill: true, tension: 0.35, pointBackgroundColor: cor,
      }],
    },
    options: opcoes,
  });
}

linha('chartPeso', 'Peso (kg)', dadosGrafico.peso, '#E8531D', 'rgba(232,83,29,0.15)');
linha('chartGordura', '% Gordura', dadosGrafico.gordura, '#E8531D', 'rgba(232,83,29,0.15)');

// Expandir/recolher detalhes de cada medição
document.querySelectorAll('.btn-expandir').forEach(btn => {
  btn.addEventListener('click', () => {
    const alvo = document.getElementById(btn.closest('tr').dataset.target);
    const aberto = alvo.style.display !== 'none';
    alvo.style.display = aberto ? 'none' : 'table-row';
    btn.textContent = aberto ? 'Ver mais ▾' : 'Ver menos ▴';
  });
});
