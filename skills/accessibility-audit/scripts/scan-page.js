/* Evaluate in the audited page only through an approved execution API.
 * Load bundled axe.min.js first. This expression returns a Promise result.
 */
(async () => {
  const url = window.location.href;
  const startedAt = new Date().toISOString();
  const standard = 'WCAG 2.1 A/AA automated checks';
  const options = {
    runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']},
    resultTypes: ['violations', 'incomplete', 'passes', 'inapplicable']
  };
  try {
    if (!window.axe || window.axe.version !== '4.14.0') {
      throw new Error('Bundled axe-core 4.14.0 is not loaded in this page');
    }
    const result = await window.axe.run(document, options);
    if (!Array.isArray(result.violations) || !Array.isArray(result.incomplete)) {
      throw new Error('Scanner returned an incomplete findings payload');
    }
    if (window.location.href !== url) throw new Error('Page navigated during scan');
    const rules = rows => rows.map(rule => ({
      id: rule.id, impact: rule.impact ?? null, help: rule.help,
      helpUrl: rule.helpUrl, tags: rule.tags,
      nodes: rule.nodes.map(node => ({
        target: node.target, html: node.html,
        failureSummary: node.failureSummary ?? '',
        any: node.any, all: node.all, none: node.none
      }))
    }));
    return {
      url, status: 'COMPLETED', startedAt, completedAt: new Date().toISOString(),
      standard, scanner: result.testEngine, testRunner: result.testRunner,
      testEnvironment: result.testEnvironment, scanOptions: options,
      viewport: {width: window.innerWidth, height: window.innerHeight},
      title: document.title, violations: rules(result.violations),
      incomplete: rules(result.incomplete),
      passes: result.passes.map(rule => ({id: rule.id, nodes: rule.nodes.length})),
      inapplicable: result.inapplicable.map(rule => rule.id)
    };
  } catch (error) {
    return {url, status: 'FAILED', startedAt, completedAt: new Date().toISOString(),
      standard, error: String(error?.message ?? error)};
  }
})()
