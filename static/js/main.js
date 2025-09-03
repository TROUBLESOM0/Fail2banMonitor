/**
 * Fail2ban Banned IPs Monitor - Frontend JavaScript
 * Version: v2.0.1
 * Description: DataTables initialization and AJAX functionality for IP monitoring dashboard
 * Date: August 2025
 */

$(document).ready(function() {
    // Initialize DataTables
    $('#bannedIpsTable').DataTable({
        responsive: true,
        pageLength: 25,
        order: [[2, 'desc']], // Sort by banned date descending
        columnDefs: [
            {
                targets: 3, // Actions column
                orderable: false,
                searchable: false
            }
        ],
        language: {
            search: "Search IPs:",
            lengthMenu: "Show _MENU_ IPs per page",
            info: "Showing _START_ to _END_ of _TOTAL_ banned IPs",
            infoEmpty: "No banned IPs found",
            infoFiltered: "(filtered from _MAX_ total IPs)",
            emptyTable: "No banned IPs currently in the system"
        }
    });

    // Refresh button functionality
    $('#refreshBtn').click(function() {
        const $btn = $(this);
        const originalText = $btn.html();
        
        // Show loading state
        $btn.prop('disabled', true);
        $btn.html('<i class="fas fa-spinner fa-spin me-1"></i>Refreshing...');
        
        // Call refresh API
        $.ajax({
            url: '/api/refresh',
            method: 'GET',
            timeout: 30000,
            success: function(response) {
                if (response.success) {
                    showAlert('success', 'Banned IPs refreshed successfully! Reloading page...');
                    // Reload page after short delay
                    setTimeout(function() {
                        window.location.reload();
                    }, 1500);
                } else {
                    showAlert('danger', 'Failed to refresh banned IPs: ' + (response.error || 'Unknown error'));
                }
            },
            error: function(xhr, status, error) {
                let errorMsg = 'Failed to refresh banned IPs';
                if (status === 'timeout') {
                    errorMsg += ': Request timed out';
                } else if (xhr.responseJSON && xhr.responseJSON.error) {
                    errorMsg += ': ' + xhr.responseJSON.error;
                } else {
                    errorMsg += ': ' + error;
                }
                showAlert('danger', errorMsg);
            },
            complete: function() {
                // Restore button state
                $btn.prop('disabled', false);
                $btn.html(originalText);
            }
        });
    });

    // Auto-refresh every 5 minutes (in addition to hourly server updates)
    setInterval(function() {
        console.log('Auto-refreshing page...');
        window.location.reload();
    }, 5 * 60 * 1000); // 5 minutes


    // Click handler for IP addresses to copy to clipboard
    $(document).on('click', '.ip-address', function() {
        const ip = $(this).text();
        const $element = $(this);
        
        // Try to copy to clipboard
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(ip).then(function() {
                showCopyBubble($element, ip);
            }).catch(function() {
                // Fallback for older browsers
                copyToClipboardFallback(ip, $element);
            });
        } else {
            copyToClipboardFallback(ip, $element);
        }
    });

    // Fallback clipboard copy method
    function copyToClipboardFallback(text, $element) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            document.execCommand('copy');
            showCopyBubble($element, text);
        } catch (err) {
            console.error('Failed to copy text: ', err);
            showAlert('warning', 'Failed to copy IP address to clipboard', 3000);
        } finally {
            document.body.removeChild(textArea);
        }
    }

    // Start countdown timer for next update (updates every hour)
    startCountdownTimer();

    // Start current time display
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
});

// Function to update current time display
function updateCurrentTime() {
    const now = new Date();
    const options = {
        timeZone: 'America/Chicago',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
    };
    const timeString = now.toLocaleString('en-US', options).replace(',', '');
    $('#time-display').text(timeString + ' CST');
}

// Start countdown timer for next update
function startCountdownTimer() {
    function updateCountdown() {
        // Updates happen every hour at the top of the hour
        const now = new Date();
        const nextHour = new Date(now);
        nextHour.setHours(nextHour.getHours() + 1, 0, 0, 0); // Next hour at :00
        
        const timeUntilUpdate = nextHour - now;
        
        if (timeUntilUpdate > 0) {
            const minutes = Math.floor(timeUntilUpdate / (1000 * 60));
            const seconds = Math.floor((timeUntilUpdate % (1000 * 60)) / 1000);
            
            const formattedTime = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            $('#countdown-display').text(formattedTime);
        } else {
            $('#countdown-display').text('Updating...');
        }
    }
    
    // Update immediately
    updateCountdown();
    
    // Update every second
    setInterval(updateCountdown, 1000);
}

// Utility function to show alerts
function showAlert(type, message, autoHide = 5000) {
    const alertId = 'alert-' + Date.now();
    const alertHtml = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            <i class="fas fa-${getIconForAlertType(type)} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    $('#alertArea').append(alertHtml);
    
    // Auto-hide after specified time
    if (autoHide > 0) {
        setTimeout(function() {
            $('#' + alertId).fadeOut(function() {
                $(this).remove();
            });
        }, autoHide);
    }
}

// Get appropriate icon for alert type
function getIconForAlertType(type) {
    const icons = {
        'success': 'check-circle',
        'danger': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// Show copy bubble notification near the clicked element
function showCopyBubble($element, ip) {
    // Create bubble element
    const bubbleId = 'copy-bubble-' + Date.now();
    const bubble = $(`
        <div id="${bubbleId}" class="copy-bubble">
            <i class="fas fa-check-circle me-1"></i>
            Copied ${ip}!
        </div>
    `);
    
    // Get position of clicked element
    const offset = $element.offset();
    const elementHeight = $element.outerHeight();
    
    // Position bubble above the clicked element
    bubble.css({
        position: 'absolute',
        top: offset.top - 40,
        left: offset.left,
        zIndex: 9999
    });
    
    // Add to body and show with animation
    $('body').append(bubble);
    bubble.fadeIn(200);
    
    // Remove after 2 seconds
    setTimeout(function() {
        bubble.fadeOut(300, function() {
            bubble.remove();
        });
    }, 2000);
}
