import subprocess
import sys

def test_pluk_entry_point(capfd):
    # simulate calling the CLI main function directly
    from pluk.cli import main
    main()
    captured = capfd.readouterr()
    assert 'pluk: symbol search engine CLI' in captured.out
