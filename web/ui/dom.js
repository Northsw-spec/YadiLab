export const $ = id => document.getElementById(id);
export const el = (tag, attrs = {}, ...children) => {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key.startsWith('on') && typeof value === 'function') node.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === 'className') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key === 'value') node.value = value;
    else if (key === 'checked') node.checked = Boolean(value);
    else if (key === 'disabled') node.disabled = Boolean(value);
    else if (key === 'dataset') Object.assign(node.dataset, value);
    else node.setAttribute(key, String(value));
  }
  for (const item of children.flat(3)) {
    if (item == null || item === false) continue;
    node.append(item instanceof Node ? item : document.createTextNode(String(item)));
  }
  return node;
};
export const field = (title, control) => el('div', {className: 'field'}, el('label', {htmlFor: control.id || ''}, title), control);
export const heading = title => el('h3', {className: 'section-title'}, title);
export const small = text => el('p', {className: 'muted tiny'}, text);
export const button = (text, onclick, variant = 'btn-outline', attrs = {}) =>
  el('button', {type: 'button', className: `btn ${variant}`, onclick, ...attrs}, text);
export const input = (value, change, attrs = {}) => {
  const control = el('input', {type: 'text', className: 'control', value: value ?? '', ...attrs});
  control.addEventListener('change', () => change(control.value));
  return control;
};
export const dropdown = (options, selected, change, attrs = {}) => {
  const control = el('select', {className: 'control', ...attrs});
  for (const option of options) control.append(el('option', {value: option.value}, option.label));
  control.value = selected == null ? '' : String(selected);
  control.addEventListener('change', () => change(control.value));
  return control;
};
export const check = (label, checked, onChange) => {
  const control = el('input', {type: 'checkbox', checked});
  control.addEventListener('change', () => onChange(control.checked));
  return el('label', {className: 'check-line'}, control, label);
};
