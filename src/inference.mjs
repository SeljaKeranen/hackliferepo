/** Same exported standardisation and coefficients used by Python. No network inference. */
export function ridgeDelta(model, features) {
  const x = model.features.map(k => features[k]);
  if (x.some(v => !Number.isFinite(v))) throw new Error('Missing or invalid model input');
  return model.intercept + x.reduce((sum, v, i) => sum + model.coefficients[i] * (v - model.mean[i]) / model.scale[i], 0);
}
export function predictScenario(model, country, changes = {}, horizon = 5) {
  if (![5, 10].includes(horizon)) throw new Error('Unsupported horizon');
  const f = {...country.features};
  f.health_spending += Number(changes.health || 0);
  f.pm25 *= 1 + Number(changes.pollution || 0) / 100;
  f.log_gdp += Math.log(1 + Number(changes.gdp || 0) / 100);
  const outside = model.features.filter(k => !Number.isFinite(f[k]) || f[k] < model.bounds[k][0] || f[k] > model.bounds[k][1]);
  if (outside.length) return {available: false, outside, value: null, first: null};
  const step = features => model.selected === 'ridge' ? ridgeDelta(model, features) : model.selected === 'trend' ? features.past_change : 0;
  const delta = step(f), first = f.life_expectancy + delta;
  if (horizon === 5) return {available: true, outside: [], value: first, first};
  const next = {...f, life_expectancy: first, past_change: delta};
  const nextOutside = model.features.filter(k => next[k] < model.bounds[k][0] || next[k] > model.bounds[k][1]);
  if (nextOutside.length) return {available:false,outside:nextOutside,value:null,first};
  return {available: true, outside: [], value: first + step(next), first};
}
