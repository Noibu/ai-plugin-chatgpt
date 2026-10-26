/* Shared report picker; retained checkout asset/function names for compatibility.
   Local selections only. Dispatch requests a scoped conversation turn. */
function bindCheckoutSchedule(root, form, getSelected, dispatch, status) {
  const field = name => form.elements.namedItem(name);
  const days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
  const controls = [...form.querySelectorAll('input[name="outputs"]')];
  const sync = () => {
    const frequency = field('frequency').value;
    form.querySelector('[data-weekday]').hidden = !['weekly','biweekly'].includes(frequency);
    form.querySelector('[data-monthday]').hidden = frequency !== 'monthly';
    form.querySelector('[data-anchor]').hidden = frequency !== 'biweekly';
    field('startDate').required = frequency === 'biweekly';
    field('monthday').required = frequency === 'monthly';
    field('startDate').disabled = frequency !== 'biweekly';
    field('monthday').disabled = frequency !== 'monthly';
    for (const row of form.querySelectorAll('[data-output]')) row.hidden = !controls.some(c => c.checked && c.value === row.dataset.output);
    for (const button of form.querySelectorAll('[data-time]')) button.setAttribute('aria-pressed',String(button.dataset.time === field('time').value));
  };
  form.addEventListener('change', sync);
  for (const button of form.querySelectorAll('[data-time]')) button.addEventListener('click', () => {field('time').value = button.dataset.time; sync();});
  form.querySelector('[data-cancel-schedule]').addEventListener('click', () => {
    form.hidden = true;
    status.textContent = 'Schedule setup cancelled. No schedule was created.';
  });
  form.addEventListener('submit', event => {
    event.preventDefault();
    const action = getSelected();
    if (form.hidden || !action || !form.reportValidity()) return;
    const frequency = field('frequency').value;
    const time = field('time').value;
    const timezone = field('timezone').value.trim();
    const detail = field('detail').value;
    const frequencies = root.dataset.noibuWorkflow === 'store-pulse' ? ['daily','weekly','biweekly','monthly'] : ['weekly','biweekly','monthly'];
    if (!frequencies.includes(frequency) || !['summary','full'].includes(detail) || !/^([01]\d|2[0-3]):[0-5]\d$/.test(time)) {
      status.textContent = 'Choose a valid frequency, time and report detail.'; return;
    }
    if (!timezone) {status.textContent = 'Confirm the timezone before requesting a schedule.'; return;}
    try {new Intl.DateTimeFormat('en',{timeZone:timezone}).format(new Date());}
    catch {status.textContent = 'Use a valid IANA timezone, such as America/Toronto.'; return;}
    const settings = {frequency,time,timezone,detail,outputs:[]};
    if (['weekly','biweekly'].includes(frequency)) {
      settings.weekday = field('weekday').value;
      if (!days.includes(settings.weekday)) {status.textContent = 'Choose a valid weekday.'; return;}
    }
    if (frequency === 'biweekly') {
      const value = field('startDate').value;
      const date = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(value + 'T12:00:00Z') : null;
      if (!date || !Number.isFinite(date.valueOf()) || date.toISOString().slice(0,10) !== value || days[(date.getUTCDay()+6)%7] !== settings.weekday) {
        status.textContent = 'Choose a first run date matching the selected weekday.'; return;
      }
      settings.startDate = value;
    }
    if (frequency === 'monthly') {
      settings.monthday = Number(field('monthday').value);
      if (!Number.isInteger(settings.monthday) || settings.monthday < 1 || settings.monthday > 28) {status.textContent = 'Choose a day of month from 1 to 28.'; return;}
    }
    for (const control of controls.filter(c => c.checked)) {
      const delivery = control.value;
      if (!['email','slack','notion','chatgpt','connected-app'].includes(delivery)) {status.textContent = 'Choose a supported delivery option.'; return;}
      const destinationName = {email:'emailDestination',slack:'slackDestination',notion:'notionDestination','connected-app':'otherDestination'}[delivery];
      const providerName = {email:'emailProvider','connected-app':'otherProvider'}[delivery];
      const output = {delivery};
      if (destinationName && field(destinationName).value.trim()) output.destination = field(destinationName).value.trim();
      if (providerName && field(providerName).value.trim()) output.provider = field(providerName).value.trim();
      if ((output.destination || '').length > 300 || (output.provider || '').length > 100 || /[\x00-\x1f\x7f]/.test((output.destination || '') + (output.provider || ''))) {
        status.textContent = 'Use short destination/account hints without control characters.'; return;
      }
      settings.outputs.push(output);
    }
    if (!settings.outputs.length) {status.textContent = 'Choose at least one delivery option.'; return;}
    dispatch({...action,schedule:settings},form.querySelector('button[type="submit"]'));
  });
  sync();
}
