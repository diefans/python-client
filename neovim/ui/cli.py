"""CLI for accessing the gtk/tickit UIs implemented by this package."""
import os
import shlex

import click
import yaml

from .ui_bridge import UIBridge
from .. import attach


CONFIG_FILES = (
    '.pynvim.yaml',
    '~/.pynvim.yaml',
    '~/.config/pynvim/config.yaml'
)


def load_config(config_file):
    """Load config values from yaml."""

    if config_file:
        with open(config_file) as f:
            return yaml.load(f)

    else:
        for config_file in CONFIG_FILES:
            try:
                with open(os.path.expanduser(config_file)) as f:
                    return yaml.load(f)

            except IOError:
                pass

    return {}


@click.command(context_settings=dict(allow_extra_args=True))
@click.option('--prog')
@click.option('--notify', '-n', default=False, is_flag=True)
@click.option('--listen', '-l')
@click.option('--connect', '-c')
@click.option('--profile',
              default='disable',
              type=click.Choice(['ncalls', 'tottime', 'percall', 'cumtime',
                                 'name', 'disable']))
@click.option('config_file', '--config', type=click.Path(exists=True))
@click.pass_context
def main(ctx, prog, notify, listen, connect, profile, config_file):
    """Entry point."""

    address = connect or listen


    if address:
        import re
        p = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:\:\d{1,5})?$')

        if p.match(address):
            args = ('tcp',)
            kwargs = {'address': address}
        else:
            args = ('socket',)
            kwargs = {'path': address}

    if connect:
        # connect to existing instance listening on address
        nvim = attach(*args, **kwargs)
    elif listen:
        # spawn detached instance listening on address and connect to it
        import os
        import time
        from subprocess import Popen
        os.environ['NVIM_LISTEN_ADDRESS'] = address
        nvim_argv = shlex.split(prog or 'nvim --headless') + ctx.args
        # spawn the nvim with stdio redirected to /dev/null.
        dnull = open(os.devnull)
        p = Popen(nvim_argv, stdin=dnull, stdout=dnull, stderr=dnull)
        dnull.close()
        while p.poll() or p.returncode is None:
            try:
                nvim = attach(*args, **kwargs)
                break
            except IOError:
                # socket not ready yet
                time.sleep(0.050)
    else:
        # spawn embedded instance
        nvim_argv = shlex.split(prog or 'nvim --embed') + ctx.args
        nvim = attach('child', argv=nvim_argv)

    from .gtk_ui import GtkUI
    config = load_config(config_file)
    ui = GtkUI(config)
    bridge = UIBridge()
    bridge.connect(nvim, ui, profile if profile != 'disable' else None, notify)


if __name__ == '__main__':
    main()
