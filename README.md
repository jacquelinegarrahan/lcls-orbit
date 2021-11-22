# lcls-orbit

This repository contains orbit-specific GUI tooling for LCLS.

## Demo

The demo can be run using a port forwarding to the lcls network with `lcls-live` or on the dev network with the proper prod-on-dev EPICS script sourced.


### First, create the `lcls-orbit` conda environment:
An environment file is packaged in examples. This may be used to create an appropriate environment:

```
$ conda env create -f examples/environment.yml
```

Now, activate this environment:
```
$ conda activate lcls-orbit
```

### Configure Remote EPICS access (optional)

The `lcls-live` utility functions allow configuring remote access to EPICS variables. In order to do this, the following variables must be set:

| Variable             | Description                          |
|----------------------|--------------------------------------|
| CA_NAME_SERVER_PORT  | Port for forwarding                  |
| LCLS_PROD_HOST       | Production host of process variables |
| SLAC_MACHINE         | Public SLAC machine for forwarding   |
| SLAC_USERNAME        | Username passed to ssh               |
| EPICS_CA_NAME_SERVERS| localhost:$CA_NAME_SERVER_PORT       |

Once evironment variables are set, remote EPICS access may be configured in the bridge shell using the command:

```
$ configure-epics-remote
```

### Launch client
```
$ bokeh serve examples/client.py --show
```


# TODO
- [x] Table variable/monitor
- [x] Sample widget
- [x] Example (with lcls-live)
- [ ] Passable labels for z areas
- [ ] Entry for axis extents. Not available in current bokeh tooltips
- [ ] Documentation
- [x] dynamic width for markers
- [ ] LUME-EPICS improvement projects. Scalable controller service etc.
