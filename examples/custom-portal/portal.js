fetch('/captivate/token', { cache: 'no-store' })
  .then(response => {
    if (!response.ok) throw new Error('Access form unavailable');
    return response.json();
  })
  .then(data => {
    document.getElementById('token').value = data.token;
    document.getElementById('continue').disabled = false;
    document.getElementById('status').textContent = '';
  })
  .catch(() => {
    document.getElementById('status').textContent = 'Reload this page to prepare the access form.';
  });
