# gtt-watch

On AMD APUs (Ryzen with integrated graphics) the GPU has only a small dedicated memory carve-out.
Everything beyond it is GTT memory taken from system RAM. When gnome-shell leaks GPU buffers, it can
quietly hold gigabytes this way, and the only fix is to log out and back in. gtt-watch shows how much
GTT memory a process holds and warns above a limit.

It reads `drm-memory-gtt` from `/proc/<pid>/fdinfo`, which needs no root, and counts every DRM client
once, even when it has several files open. The amdgpu driver publishes these numbers on current
kernels.

## Install

```sh
pip install git+https://github.com/ulliiiiiiiii/gtt-watch
```

No dependencies besides Python 3.10+ and `pgrep`; `notify-send` for desktop notifications.

## Usage

```sh
gtt-watch                          # gnome-shell: 412 MB GTT
gtt-watch --limit 1536 --notify    # exit status 2 and a desktop notification above 1536 MB
gtt-watch --process Xwayland
```

Exit status: 0 below the limit, 2 above it, 1 when the process is not running or the kernel publishes no
GTT figure for it (an unknown value is never reported as 0 MB).

## Check every 15 minutes

`~/.config/systemd/user/gtt-watch.service`:

```ini
[Unit]
Description=Check the GTT memory of gnome-shell

[Service]
Type=oneshot
ExecStart=%h/.local/bin/gtt-watch --limit 1536 --notify
```

`~/.config/systemd/user/gtt-watch.timer`:

```ini
[Unit]
Description=Check the GTT memory of gnome-shell every 15 minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=15min

[Install]
WantedBy=timers.target
```

Then run `systemctl --user enable --now gtt-watch.timer`.

## License

MIT
