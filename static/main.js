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

    function initMentions(textarea) {
        const dropdown = document.createElement('div');
        dropdown.className = 'mention-dropdown list-group position-absolute';
        dropdown.style.display = 'none';
        textarea.parentNode.style.position = 'relative';
        textarea.parentNode.appendChild(dropdown);

        let start = null;

        textarea.addEventListener('input', () => {
            const pos = textarea.selectionStart;
            const value = textarea.value;

            if (start === null && value[pos - 1] === '@') {
                start = pos - 1;
            }

            if (start !== null) {
                if (pos < start || value[start] !== '@') {
                    start = null;
                    dropdown.style.display = 'none';
                    return;
                }
                const query = value.slice(start + 1, pos);
                if (/\s/.test(query)) {
                    dropdown.style.display = 'none';
                    return;
                }
                fetch('/api/users?q=' + encodeURIComponent(query))
                    .then(r => r.json())
                    .then(data => {
                        dropdown.innerHTML = '';
                        data.users.forEach(user => {
                            const item = document.createElement('button');
                            item.type = 'button';
                            item.className = 'list-group-item list-group-item-action';
                            item.textContent = user;
                            item.addEventListener('mousedown', e => {
                                e.preventDefault();
                                const before = value.slice(0, start);
                                const after = value.slice(pos);
                                textarea.value = `${before}@${user} ${after}`;
                                const newPos = before.length + user.length + 2;
                                textarea.setSelectionRange(newPos, newPos);
                                dropdown.style.display = 'none';
                                start = null;
                            });
                            dropdown.appendChild(item);
                        });
                        dropdown.style.display = data.users.length ? 'block' : 'none';
                    });
            }
        });

        textarea.addEventListener('blur', () => {
            setTimeout(() => dropdown.style.display = 'none', 200);
        });
    }

    document.querySelectorAll('textarea.mention-enabled').forEach(initMentions);
});
