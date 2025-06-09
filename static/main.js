// Bootstrap validation and Kanban drag & drop
window.addEventListener('DOMContentLoaded', () => {
    // Form validation using Bootstrap styles
    document.querySelectorAll('form').forEach(form => {
        if (form.hasAttribute('novalidate')) return;
        form.classList.add('needs-validation');
        form.addEventListener('submit', e => {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Drag & drop for kanban cards and detail popup
    let dragging = false;
    document.querySelectorAll('.kanban-card').forEach(card => {
        card.addEventListener('dragstart', ev => {
            dragging = true;
            ev.dataTransfer.setData('text/plain', card.dataset.id);
            ev.dataTransfer.setData('text/model', card.dataset.model);
        });
        card.addEventListener('dragend', () => { dragging = false; });
        card.addEventListener('click', () => {
            if (dragging) { dragging = false; return; }
            const id = card.dataset.id;
            const model = card.dataset.model;
            fetch(`/api/record/${model}/${id}`).then(r => r.json()).then(data => {
                const body = document.getElementById('recordOffcanvasBody');
                const label = document.getElementById('recordOffcanvasLabel');
                if (label) label.textContent = data.name || `${model} ${id}`;
                if (body) {
                    body.innerHTML = '';
                    Object.entries(data).forEach(([k, v]) => {
                        if (k === '_sa_instance_state' || v === null) return;
                        const p = document.createElement('p');
                        p.innerHTML = `<strong>${k}:</strong> ${v}`;
                        body.appendChild(p);
                    });
                }
                const el = document.getElementById('recordOffcanvas');
                const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(el);
                offcanvas.show();
            });
        });
    });

    document.querySelectorAll('.kanban-column').forEach(col => {
        col.addEventListener('dragover', ev => ev.preventDefault());
        col.addEventListener('drop', ev => {
            ev.preventDefault();
            const id = ev.dataTransfer.getData('text/plain');
            const model = ev.dataTransfer.getData('text/model');
            const status = col.dataset.status;
            const card = document.querySelector(`.kanban-card[data-id='${id}'][data-model='${model}']`);
            if (card && status) {
                col.querySelector('.cards').appendChild(card);
                fetch('/api/update_status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ model, id, status })
                });
            }
        });
    });
});
