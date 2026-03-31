# New Feature - v0.7.0

This document describes a new feature to add to the `bh-analyze-systems` utility which will make up the changes required for the next version of the tool (v0.7.0)

## Background

Each system consists of 32 chips (represented as bus_ids) each with their own set of Ethernet ports (eth_ids). The 32 chips are spread across 4 UBB's (8 chips each) and the ports are connected together in some configuration (via cables or other means).

Each UBB is the same board. For example, bus_ids 01:00.0, 41:00.0, c1:00.0 and 81:00.0 represent chip 1 on UBB 1, 2, 3, and 4. This means that all of the PCB trace paths for the high-speed Serdes lanes routing to other Ethernet ports are the same across the 4 UBBs.

When looking for patterns of behavior across multiple systems we should be able to view the data on a per-UBB basis instead of a per-system basis which is the current implementation. For example, when we look at PRBS data for ETH10, serdes lane 4 on bus_ids 01:00.0, 41:00.0, c1:00.0 and 81:00.0, we should be able to look at this data as if we have 4 samples for chip 1 (U1), ETH10, serdes lane 4 rather than 1 sample for chip 1 on each UBB.

## Current Implementation

`bh-analyze-systems` currently looks at the data separately for each bus_id/eth_id on all the systems. This current funcionality should remain and should NOT be changed.

## New Feature

Add an option to view the data on a per-UBB basis rather than a per-system basis which will 4x the amount of data we have for a particular UBB serdes lane as we consider chips 0x:00.0, 4x:00.0, cx:00.0, and 8x:00.0 as the same in that we don't care which UBB on the system it is, we just care that it is chip x.
