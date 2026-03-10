# QSFP Port Mapping

Add a new feature to the `bh-topology` tool that provides port-to-port mapping of cable-connected ports using a specific cable-configuration file provided by the user

## Prerequisite Info

- There may be multiple types of cable configurations so the user would need to specify which configuration file to use
- If no cable configuration file is provided, simply return the QSFP port number for a cable-connected port as is currently implemented

## QC3 Cable Configuration (Example config file)

UBB1:

- QSFP-1 <> QSFP-2
- QSFP-3 <> QSFP-5
- QSFP-4 <> QSFP-6
- QSFP-7 <> QSFP-8
- QSFP-9 <> QSFP-10
- QSFP-11 <> QSFP-12
- QSFP-13 <> QSFP-14

UBB2: same as UBB1
UBB3: same as UBB1
UBB4: same as UBB1

### Example usage

Get the port connected to 01:00.0 ETH10 using the cable configuration used for QC3 testing
`bh-topology 01:00.0 ETH10 QC3`
