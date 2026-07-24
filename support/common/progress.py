from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

progress_bar = None


def start(progress_title: str, progress_bar_max: int) -> None:
    global progress_bar
    if progress_bar is None:
        progress_bar = Progress(
            TextColumn("[progress.description]{task.description} ->"),
            MofNCompleteColumn(),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
        )
        progress_bar.start()
    progress_task = progress_bar.add_task(progress_title, total=progress_bar_max)
    progress_bar.start_task(progress_task)
    return progress_task


def advance(progress_task: int) -> None:
    global progress_bar
    assert progress_bar is not None
    assert progress_task is not None
    progress_bar.update(progress_task, advance=1)


def end(progress_task: int) -> None:
    global progress_bar
    assert progress_task is not None
    progress_bar.stop_task(progress_task)
    end_progress_bar = True
    with progress_bar._lock:
        for task in progress_bar._tasks.values():
            if task.stop_time is None:
                end_progress_bar = False
    if end_progress_bar == True:
        progress_bar.stop()
        progress_bar = None
