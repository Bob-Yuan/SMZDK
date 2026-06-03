// Auto-hide flash messages after 4 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.transition = 'opacity 0.5s ease';
            alert.style.opacity = '0';
            setTimeout(function() {
                alert.remove();
            }, 500);
        }, 4000);
    });

    // Mobile nav toggle - close when clicking outside
    document.addEventListener('click', function(e) {
        const navActions = document.querySelector('.nav-actions');
        const navToggle = document.querySelector('.nav-toggle');
        if (navActions && navActions.classList.contains('show') &&
            !navActions.contains(e.target) && !navToggle.contains(e.target)) {
            navActions.classList.remove('show');
        }
    });
});
