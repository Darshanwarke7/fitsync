// FitSync shared front-end helpers

// Auto-dismiss alerts after 4s
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".alert").forEach((el) => {
    setTimeout(() => {
      const alert = bootstrap.Alert.getOrCreateInstance(el);
      if (alert) alert.close();
    }, 4000);
  });
});

function toggleSidebar() {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebarOverlay");
  if (!sidebar) return;
  sidebar.classList.toggle("open");
  if (overlay) overlay.classList.toggle("open", sidebar.classList.contains("open"));
}

function closeSidebar() {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebarOverlay");
  if (sidebar) sidebar.classList.remove("open");
  if (overlay) overlay.classList.remove("open");
}

// Auto-close the mobile sidebar after tapping a nav link
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".sidebar a").forEach((link) => {
    link.addEventListener("click", () => {
      if (window.innerWidth <= 900) closeSidebar();
    });
  });
});

// Generic helper to add a dynamic exercise row on the "Record Workout" form
function addExerciseRow() {
  const container = document.getElementById("exercise-rows");
  if (!container) return;
  const row = document.createElement("div");
  row.className = "row g-2 align-items-center mb-2 exercise-row";
  row.innerHTML = `
    <div class="col-md-3">
      <select name="muscle_group[]" class="form-select form-select-sm" required>
        <option value="Chest">Chest</option>
        <option value="Back">Back</option>
        <option value="Legs">Legs</option>
        <option value="Shoulders">Shoulders</option>
        <option value="Arms">Arms</option>
        <option value="Core">Core</option>
        <option value="Cardio">Cardio</option>
        <option value="Full Body">Full Body</option>
      </select>
    </div>
    <div class="col-md-3"><input type="text" name="exercise_name[]" class="form-control form-control-sm" placeholder="Exercise name" required></div>
    <div class="col-md-1"><input type="number" name="sets[]" class="form-control form-control-sm" placeholder="Sets" min="0"></div>
    <div class="col-md-1"><input type="number" name="reps[]" class="form-control form-control-sm" placeholder="Reps" min="0"></div>
    <div class="col-md-1"><input type="number" step="0.5" name="weight_kg[]" class="form-control form-control-sm" placeholder="Kg" min="0"></div>
    <div class="col-md-2"><input type="number" name="duration_min[]" class="form-control form-control-sm" placeholder="Min" min="0"></div>
    <div class="col-md-1"><button type="button" class="btn btn-sm btn-outline-danger" onclick="this.closest('.exercise-row').remove()"><i class="bi bi-trash"></i></button></div>
  `;
  container.appendChild(row);
}

// Fetch AI suggestions and render into a target element
async function fetchAI(url, targetId, renderFn) {
  const target = document.getElementById(targetId);
  if (!target) return;
  target.innerHTML = '<div class="text-muted small"><span class="spinner-border spinner-border-sm"></span> Generating AI suggestion...</div>';
  try {
    const res = await fetch(url);
    const data = await res.json();
    target.innerHTML = renderFn(data);
  } catch (err) {
    target.innerHTML = '<div class="text-danger small">Could not generate AI suggestion right now.</div>';
  }
}
