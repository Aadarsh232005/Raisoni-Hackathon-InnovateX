// Clock
const clockEl = document.getElementById('clock');
function updateClock() {
  if (clockEl) {
    clockEl.textContent = new Date().toLocaleTimeString('en-IN', {
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
  }
}
updateClock();
setInterval(updateClock, 1000);

// Mobile sidebar toggle
const toggleBtn = document.getElementById('sidebarToggle');
const sidebar   = document.getElementById('sidebar');
if (toggleBtn && sidebar) {
  toggleBtn.addEventListener('click', () => sidebar.classList.toggle('open'));
  document.addEventListener('click', e => {
    if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target))
      sidebar.classList.remove('open');
  });
}

// Auto-dismiss alerts after 5 seconds
document.querySelectorAll('.alert').forEach(alert => {
  setTimeout(() => {
    const inst = bootstrap.Alert.getOrCreateInstance(alert);
    if (inst) inst.close();
  }, 5000);
});