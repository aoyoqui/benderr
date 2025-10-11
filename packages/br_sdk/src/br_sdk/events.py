from blinker import signal

step_started = signal("step_started")
step_ended = signal("step_ended")

log_msg = signal("log_msg")
