import { useMemo } from "react";

import type { ManagerTask } from "../lib/types";

export function AssignedWorkPanel({
  tasks,
  onStatusChange
}: {
  tasks: ManagerTask[];
  onStatusChange: (task: ManagerTask, status: "COMPLETED" | "BLOCKED") => void;
}) {
  const openTasks = useMemo(() => {
    const seen = new Set<string>();
    return tasks.filter((task) => {
      if (task.status !== "OPEN") return false;
      const taskKey = `${task.store_id}:${task.task_type}:${task.title}`;
      if (seen.has(taskKey)) return false;
      seen.add(taskKey);
      return true;
    });
  }, [tasks]);

  if (openTasks.length === 0) return null;

  return (
    <section className="taskStrip" data-testid="my-tasks">
      <div>
        <p className="eyebrow">Assigned work</p>
        <h3>{openTasks.length} open tasks</h3>
      </div>
      <div className="taskQueue">
        {openTasks.map((task) => (
          <article key={task.task_id} className="taskRow">
            <div>
              <strong>{task.title}</strong>
              <span>{task.store_name ?? task.store_id} / {task.priority} / {task.status}</span>
            </div>
            <div className="taskActions">
              <button
                className="secondaryButton"
                data-testid={`complete-work-${task.task_id}`}
                onClick={() => onStatusChange(task, "COMPLETED")}
              >
                Complete
              </button>
              <button
                className="secondaryButton"
                onClick={() => onStatusChange(task, "BLOCKED")}
              >
                Block
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
