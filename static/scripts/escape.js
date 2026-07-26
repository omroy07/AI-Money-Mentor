export function esc(s) {
  const d = document.createElement('div');
  d.textContent = String(s ?? '');
  return d.innerHTML;
}
export function escAttr(s) {
  return String(s ?? '')
    .replace(/"/g, '"')
    .replace(/'/g, '&#39;');
}
