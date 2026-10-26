/* Optional read-only DOM facts. This is NOT axe or an accessibility verdict.
 * No page/global/DOM writes, network requests, form values or stored data reads.
 * Pass source only through a documented read-only DOM inspection interface.
 */
(() => {
  const limit = 150;
  const clip = value => String(value || '').replace(/\s+/g, ' ').trim().slice(0, 240);
  const target = element => {
    const parts = [];
    for (let node = element; node && node.nodeType === 1 && parts.length < 6; node = node.parentElement) {
      let index = 1;
      for (let sibling = node.previousElementSibling; sibling; sibling = sibling.previousElementSibling) {
        if (sibling.localName === node.localName) index++;
      }
      parts.unshift(node.localName + ':nth-of-type(' + index + ')');
    }
    return parts.join(' > ');
  };
  const all = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6,main,nav,header,footer,img,button,a,input,select,textarea,[role]'));
  const chosen = all.slice(0, limit);
  const observations = chosen.map(element => {
    const style = window.getComputedStyle(element);
    const referenced = (element.getAttribute('aria-labelledby') || '').split(/\s+/).filter(Boolean);
    return {
      target: target(element), tag: element.localName, role: element.getAttribute('role'),
      hidden: element.hidden || element.getAttribute('aria-hidden') === 'true' || style.display === 'none' || style.visibility === 'hidden',
      hasLayoutBox: element.getClientRects().length > 0,
      text: ['input','select','textarea'].includes(element.localName) || element.hasAttribute('contenteditable') || element.getAttribute('role') === 'textbox' ? '' : clip(element.innerText || element.textContent),
      ariaLabel: element.getAttribute('aria-label'),
      labelledBy: referenced.map(id => {const label = document.getElementById(id); return {id, found: !!label, text: label ? clip(label.textContent) : ''};}),
      labels: element.labels ? Array.from(element.labels).map(label => clip(label.textContent)) : [],
      alt: element.localName === 'img' ? element.getAttribute('alt') : null,
      type: element.localName === 'input' ? element.getAttribute('type') || 'text' : null,
      title: element.getAttribute('title'), tabIndex: element.getAttribute('tabindex'),
      disabled: element.hasAttribute('disabled') || element.getAttribute('aria-disabled') === 'true'
    };
  });
  return {
    schema: 'noibu.dom-observations/1', mode: 'read-only-observations',
    url: window.location.href, inspectedAt: new Date().toISOString(), title: document.title,
    language: document.documentElement.getAttribute('lang'),
    viewport: {width: window.innerWidth, height: window.innerHeight},
    matchedElements: all.length, returnedElements: chosen.length, truncated: all.length > limit,
    iframeCount: document.querySelectorAll('iframe').length,
    coverage: 'Bounded light-DOM facts only; frames, shadow roots, focus behavior, contrast and accessible-name computation are not assessed.',
    observations
  };
})()
