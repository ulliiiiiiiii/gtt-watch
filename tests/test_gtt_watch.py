import gtt_watch


def test_units_and_each_client_counts_once(tmp_path):
    (tmp_path / "10").write_text("drm-client-id:\t7\ndrm-memory-gtt:\t524288 KiB\n")
    (tmp_path / "11").write_text("drm-client-id:\t7\ndrm-memory-gtt:\t524288 KiB\n")  # same client, second file
    (tmp_path / "12").write_text("drm-client-id:\t8\ndrm-memory-gtt:\t256 MiB\n")
    (tmp_path / "13").write_text("drm-client-id:\t9\ndrm-memory-gtt:\t104857600\n")  # plain bytes
    (tmp_path / "14").write_text("pos:\t0\nflags:\t02000002\n")  # not a DRM file
    assert gtt_watch.gtt_mb(tmp_path) == 512 + 256 + 100


def test_limit_sets_the_exit_status(monkeypatch, tmp_path, capsys):
    fdinfo = tmp_path / "4242" / "fdinfo"
    fdinfo.mkdir(parents=True)
    (fdinfo / "3").write_text("drm-client-id: 1\ndrm-memory-gtt: 2048 MiB\n")
    monkeypatch.setattr(gtt_watch, "PROC", tmp_path)
    monkeypatch.setattr(gtt_watch, "find_pid", lambda name: 4242)
    assert gtt_watch.main(["--limit", "1536"]) == 2
    assert gtt_watch.main(["--limit", "4096"]) == 0
    assert gtt_watch.main([]) == 0
    assert "gnome-shell: 2048 MB GTT" in capsys.readouterr().out


def test_missing_process(monkeypatch):
    monkeypatch.setattr(gtt_watch, "find_pid", lambda name: None)
    assert gtt_watch.main(["--process", "nothing-here"]) == 1


def test_sums_before_rounding(tmp_path):
    (tmp_path / "10").write_text("drm-client-id:\t1\ndrm-memory-gtt:\t700 KiB\n")
    (tmp_path / "11").write_text("drm-client-id:\t2\ndrm-memory-gtt:\t700 KiB\n")
    assert gtt_watch.gtt_mb(tmp_path) == 1  # 1400 KiB, not 0 + 0


def test_zero_is_a_measurement(tmp_path):
    (tmp_path / "10").write_text("drm-client-id:\t1\ndrm-memory-gtt:\t0 KiB\n")
    assert gtt_watch.gtt_mb(tmp_path) == 0


def test_missing_gtt_figure_is_unknown_not_zero(monkeypatch, tmp_path, capsys):
    fdinfo = tmp_path / "4242" / "fdinfo"
    fdinfo.mkdir(parents=True)
    (fdinfo / "3").write_text("drm-client-id: 1\ndrm-memory-vram: 1024 KiB\n")  # kernel without a GTT figure
    assert gtt_watch.gtt_mb(fdinfo) is None
    monkeypatch.setattr(gtt_watch, "PROC", tmp_path)
    monkeypatch.setattr(gtt_watch, "find_pid", lambda name: 4242)
    assert gtt_watch.main(["--limit", "1536"]) == 1
    assert "no GTT figure" in capsys.readouterr().err
