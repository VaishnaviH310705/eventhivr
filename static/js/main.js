// DOM Ready
document.addEventListener('DOMContentLoaded', function() {
    // Job Search
    const jobSearch = document.getElementById('job-search');
    if (jobSearch) {
        jobSearch.addEventListener('input', function() {
            const term = this.value.toLowerCase();
            document.querySelectorAll('.job-card').forEach(card => {
                const title = card.querySelector('.job-title').textContent.toLowerCase();
                card.style.display = title.includes(term) ? 'block' : 'none';
            });
        });
    }

    // Quick Apply
    document.querySelectorAll('.btn-apply').forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.preventDefault();
            const jobId = this.dataset.jobId;
            const btn = this;
            
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Applying';
            btn.disabled = true;
            
            try {
                const response = await fetch(`/apply_job/${jobId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                const data = await response.json();
                if (data.success) {
                    btn.innerHTML = '<i class="fas fa-check"></i> Applied';
                    btn.classList.remove('btn-primary');
                    btn.classList.add('btn-success');
                } else {
                    throw new Error(data.error || 'Application failed');
                }
            } catch (error) {
                console.error('Error:', error);
                btn.innerHTML = '<i class="fas fa-times"></i> Error';
                btn.classList.add('btn-danger');
                setTimeout(() => {
                    btn.innerHTML = '<i class="fas fa-paper-plane"></i> Apply';
                    btn.disabled = false;
                    btn.classList.remove('btn-danger');
                    btn.classList.add('btn-primary');
                }, 2000);
            }
        });
    });

    // Status Counters
    async function updateStatusCounters() {
        try {
            const response = await fetch('/api/application_status');
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('applied-count').textContent = data.applied;
                document.getElementById('review-count').textContent = data.review;
                document.getElementById('interview-count').textContent = data.interview;
            }
        } catch (error) {
            console.error('Failed to load status:', error);
        }
    }
    updateStatusCounters();
});