// Navegação entre abas
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn, .panel').forEach(el => el.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
  });
});

// Cálculo automático de IMC e Massa Magra (ids gerados pelo Django: id_<campo>)
const campo = id => parseFloat(document.getElementById(id).value) || 0;

function calcular() {
  const peso = campo('id_peso');
  const alturaM = campo('id_altura') / 100;
  const gordura = campo('id_percentual_gordura');

  const imc = alturaM > 0 ? (peso / (alturaM * alturaM)).toFixed(1) : '';
  const massaMagra = peso && gordura ? (peso * (1 - gordura / 100)).toFixed(1) : '';

  document.getElementById('imc').value = imc;
  document.getElementById('imcCard').textContent = imc || '--';
  document.getElementById('massaMagra').value = massaMagra ? massaMagra + ' kg' : '';
  document.getElementById('massaMagraCard').textContent = massaMagra || '--';
  document.getElementById('gorduraCard').textContent = gordura ? gordura.toFixed(1) + '%' : '--';
}

['id_peso', 'id_altura', 'id_percentual_gordura'].forEach(id =>
  document.getElementById(id).addEventListener('input', calcular));
calcular();
