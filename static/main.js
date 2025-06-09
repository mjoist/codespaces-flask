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

    // Drag & drop for kanban cards
    document.querySelectorAll('.kanban-card').forEach(card => {
        card.addEventListener('dragstart', ev => {
            ev.dataTransfer.setData('text/plain', card.dataset.id);
            ev.dataTransfer.setData('text/model', card.dataset.model);
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
