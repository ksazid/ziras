from __future__ import annotations

import os

from huey import PostgresHuey

from common import write_results


def main():
    dsn = os.environ["TEST_DATABASE_URL"]
    huey = PostgresHuey(
        "ziras-qualification",
        dsn=dsn,
        table_prefix="ziras_q_huey",
        blocking=False,
        results=True,
    )

    @huey.task(
        name="ziras.qualify.discovery_fetch",
        retries=3,
        retry_delay=2,
        retry_backoff=2,
        priority=20,
    )
    def add(left: int, right: int) -> int:
        return left + right

    result = add(2, 3)
    pending_before = huey.pending_count()
    task = huey.dequeue()
    task_metadata_ok = bool(
        task
        and task.priority == 20
        and task.retries == 3
        and task.retry_delay == 2
        and task.retry_backoff == 2
    )

    if task is not None:
        huey.execute(task)
    value = result(blocking=True, timeout=3)

    add.schedule(args=(4, 5), delay=60, priority=30)
    scheduled_count = huey.scheduled_count()

    passed = (
        pending_before >= 1
        and task_metadata_ok
        and value == 5
        and scheduled_count >= 1
    )

    write_results(
        "huey-postgres",
        [
            {
                "id": "postgres-huey",
                "class": "background-jobs",
                "status": "PASS" if passed else "FAIL",
                "pending_before_execute": pending_before,
                "executed_result": value,
                "task_metadata_ok": task_metadata_ok,
                "scheduled_count": scheduled_count,
                "storage": "PostgreSQL",
                "production_note": "Use the application PostgreSQL database through a dedicated queue namespace; keep the queue behind a JobQueue port.",
            }
        ],
    )

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
