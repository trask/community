# How to provision an Oracle Windows bare metal runner

This guide describes a Windows equivalent of the
[Linux bare metal benchmark runner](how-to-provision-bare-metal-runner.md)
on Oracle Cloud Infrastructure (OCI).

The Windows runner is proposed, not yet provisioned. These instructions still
need to be exercised on an OCI instance before the runner is advertised as
available in [OpenTelemetry managed assets](../assets.md#bare-metal-runners).

## Before you start

Coordinate with [OpenTelemetry GitHub admins](https://github.com/orgs/open-telemetry/teams/admins)
and the [Oracle Cloud account admin](../assets.md#oracle-cloud-account).
You need permission to create OCI compute, storage, and network resources, and
GitHub organization owner access to register the runner and manage its group.

Confirm capacity and quota for a second `BM.Standard3.64` instance in the chosen
region and availability domain. This shape has 64 physical cores, 128 logical
processors, and 1024 GB of memory across two NUMA nodes.
Do not replace or share the existing Linux host.

Use an OCI-provided Windows Server license unless the account admin has confirmed
eligibility for bring-your-own licensing. Windows licensing is an additional
charge on top of compute and storage; confirm the budget and whether existing
credits cover it. See [Microsoft licensing on OCI](https://docs.oracle.com/en-us/iaas/Content/Compute/References/microsoftlicensing.htm)
and the [Oracle Cloud price list](https://www.oracle.com/cloud/price-list/#compute-os).

## Step 1: Create the instance

1. Sign in to the [Oracle Cloud Console](https://www.oracle.com/cloud/sign-in.html).
2. Navigate to **Compute**, then **Instances**, and select **Create instance**.
3. Set the following values:

   | Setting | Value |
   | --- | --- |
   | Name | `oracle-bare-metal-64cpu-1024gb-x86-64-windows-2022` |
   | Compartment | `github-self-hosted-runners` |
   | Image | Windows Server 2022 Datacenter, bare metal X9 image |
   | Shape | Bare Metal Machine, `BM.Standard3.64` |
   | Boot volume size | At least 256 GB |
   | VCN compartment | `OpenTelemetry` |
   | VCN | `vcn-20240506-1118` |
   | Subnet compartment | `OpenTelemetry` |
   | Subnet | `subnet-20240506-1118` |

   Choose a current image from the
   [Windows Server 2022 bare metal image catalog](https://docs.oracle.com/en-us/iaas/images/windows-server-2022-bm/index.htm),
   with a name beginning `Windows-Server-2022-Datacenter-Edition-BM-X9-`.
   Confirm that OCI lists `BM.Standard3.64` as compatible with the selected
   image in this region. Do not substitute a VM image or another shape without
   updating the documented hardware and runner label.
4. Review network access with the account admin. Restrict inbound RDP on TCP
   port 3389 to approved administrator addresses, or use a bastion.
   Do not allow RDP from `0.0.0.0/0`.
   Keep the runner isolated from unrelated internal services and do not give
   it OCI instance-principal permissions.
5. Allow the outbound connections required by
   [GitHub Actions](https://docs.github.com/en/actions/reference/runners/self-hosted-runners#communication),
   Windows activation and updates, and the package sources used by approved
   workflows. GitHub job dispatch uses outbound HTTPS on port 443; it does not
   require an inbound port.
6. Create the instance. Record its region, availability domain, shape, image
   name and OCID, and boot volume configuration in the admins' operational
   records.
7. Retrieve the initial password from the instance details page and
   [connect using RDP](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/connect-to-windows-instance.htm)
   as `opc`. Change the initial password and store the administrative credentials
   in the SIG GitHub Admins 1Password vault.

## Step 2: Prepare Windows

Perform host setup in an elevated PowerShell session on the new instance.
Do not run these commands on an administrator's workstation.

### Check storage and install tools

Check the capacity available to Windows:

```powershell
Get-Disk | Select-Object Number, FriendlyName, Size
Get-Volume -DriveLetter C | Select-Object DriveLetter, Size, SizeRemaining
```

If the boot volume has grown but `C:` has not, open **Disk Management**, select
**Action**, then **Rescan Disks**. Extend `C:` into the adjacent unallocated
space using **Extend Volume**. See Microsoft's
[volume extension instructions](https://learn.microsoft.com/en-us/windows-server/storage/disk-management/extend-a-basic-volume).
If another partition blocks extension, stop and consult the admins rather than
deleting a recovery or system partition.

Install:

- [Git for Windows](https://git-scm.com/downloads/win), for all users, with Git
  available from the command line and third-party software.
- [PowerShell 7](https://learn.microsoft.com/en-us/powershell/scripting/install/install-powershell-on-windows)
  using the x64 MSI installer and its **Add PowerShell to PATH** option.
  Windows PowerShell 5.1 alone does not provide the `pwsh` executable.
  Do not rely on WinGet being installed on Windows Server 2022.

Install both tools machine-wide, not only in the `opc` user profile. Open a new
PowerShell session after installation and verify:

```powershell
Get-Command git, pwsh | Select-Object Name, Source
git --version
pwsh -NoProfile -Command '$PSVersionTable.PSVersion'
```

Language SDKs should be selected by each workflow. Tools that require
administrative installation, such as Visual Studio Build Tools and Windows SDKs,
must be installed by an admin during maintenance, with their versions recorded.
Do not install the full GitHub-hosted runner image or Docker just to run
benchmarks. GitHub's job containers, service containers, and Docker actions
require Linux; Windows workflows run directly on this host.

### Set the benchmark baseline

1. Install Windows updates, verify Windows activation, and reboot until no
   installation or reboot is pending.
2. Select the **High performance** power plan in Windows Power Options.
   Record the active plan:

   ```powershell
   powercfg.exe /getactivescheme
   ```

3. Arrange a maintenance window for Windows updates, reboots, and scheduled
   antivirus scans so they do not overlap benchmark runs. Keep security updates
   and Microsoft Defender enabled; do not add broad antivirus exclusions.
4. Record the OS build, CPU, memory, and installed tool versions:

   ```powershell
   Get-CimInstance Win32_OperatingSystem |
       Select-Object Caption, Version, BuildNumber
   Get-CimInstance Win32_Processor |
       Select-Object Name, NumberOfCores, NumberOfLogicalProcessors
   Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory
   ```

Compare the totals with the expected hardware before registering the runner.
The two sockets and 128 logical processors matter for NUMA placement and Windows
processor groups. Do not assume a benchmark framework uses every processor;
record any affinity or thread-count settings with the results.

## Step 3: Register the GitHub runner

Create a separate organization runner group named
**Oracle Cloud Windows bare metal benchmark runners** in the
[organization runner-group settings](https://github.com/organizations/open-telemetry/settings/actions/runner-groups).
Use **Selected repositories** and initially grant only the repository used for
commissioning. Public repositories require explicitly enabling public repository
access on the group.

Follow [GitHub's runner-group access instructions](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/manage-access).
Repository access alone does not restrict the runner to benchmark workflows.
Restrict the group to selected trusted workflows and refs where that control is
available. Review the permitted workflows before granting access: they must not
check out or execute untrusted pull-request code or download untrusted executable
artifacts. A manual dispatch is not safe if it accepts arbitrary code to run.
This is a persistent host, not a clean machine for each job.

1. Open the [organization runner settings](https://github.com/organizations/open-telemetry/settings/actions/runners),
   select **New self-hosted runner**, then **Windows** and **x64**.
2. In an elevated PowerShell session, create and enter `C:\actions-runner`.
   Use the download and SHA-256 verification commands shown by GitHub for the
   current runner release, then extract it into this directory.
3. Run `.\config.cmd --url https://github.com/open-telemetry` and enter the
   short-lived registration token at the prompt. Do not store the token in a
   script, workflow, or operational record.
4. Answer the configuration prompts:

   | Prompt | Value |
   | --- | --- |
   | Runner group | `Oracle Cloud Windows bare metal benchmark runners` |
   | Runner name | `oracle-bare-metal-64cpu-1024gb-x86-64-windows-2022` |
   | Additional labels | `oracle-bare-metal-64cpu-1024gb-x86-64-windows-2022` |
   | Work folder | `_work` |
   | Run as a service | Yes |
   | Service account | `NT AUTHORITY\NETWORK SERVICE` |

   Keep the default `self-hosted`, `Windows`, and `X64` labels.
   The service account does not need a password or membership in
   **Administrators**. Runner setup grants access to its installation
   and work directories. Do not use the administrative `opc` account or
   `LocalSystem` for the service.
5. Confirm that exactly one runner service is installed and running:

   ```powershell
   Get-Service -Name 'actions.runner.*' |
       Select-Object Name, Status, StartType
   Get-CimInstance Win32_Service -Filter "Name LIKE 'actions.runner.%'" |
       Select-Object Name, StartName
   ```

   Check the service identity and automatic startup setting. Keep only one
   runner service on the machine so benchmark jobs from different repositories
   cannot run concurrently on it.
6. Reboot the instance, reconnect, and confirm the service is running and
   GitHub shows the runner as **Idle**.

Windows service installation happens during `config.cmd`, not through Linux's
`svc.sh`. If service setup was skipped, remove and reconfigure the runner using
[GitHub's service instructions](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/configure-the-application).
Do not run an interactive `run.cmd` process alongside the service.

## Step 4: Commission the runner

Use a trusted repository temporarily allowed by the group. Add the following
manual workflow to its default branch, then run it from that branch.
If the group restricts workflows, allow this workflow's exact path and ref.

```yaml
name: Windows benchmark runner smoke test

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  smoke-test:
    if: github.ref == format('refs/heads/{0}', github.event.repository.default_branch)
    runs-on: oracle-bare-metal-64cpu-1024gb-x86-64-windows-2022
    timeout-minutes: 10
    defaults:
      run:
        shell: pwsh
    env:
      TMP: ${{ runner.temp }}
      TEMP: ${{ runner.temp }}
    steps:
      - name: Check service environment
        run: |
          if (-not $IsWindows) {
              throw 'Expected a Windows runner'
          }
          Get-Command git, pwsh | Select-Object Name, Source
          git --version
          if ($LASTEXITCODE -ne 0) {
              throw 'Git failed'
          }
          Get-CimInstance Win32_OperatingSystem |
              Select-Object Caption, Version, BuildNumber
          Get-CimInstance Win32_Processor |
              Select-Object Name, NumberOfCores, NumberOfLogicalProcessors
          Get-PSDrive C | Select-Object Name, Used, Free
          $probe = Join-Path $env:RUNNER_TEMP 'runner-smoke-test.txt'
          if (Test-Path -LiteralPath $probe) {
              throw 'Temporary file from the previous job was not cleaned'
          }
          Set-Content -LiteralPath $probe -Value 'runner storage check'
          if ((Get-Content -LiteralPath $probe) -ne 'runner storage check') {
              throw 'Temporary storage check failed'
          }
```

Run it twice to check both service-account access and cleanup between jobs.
Then run a representative benchmark workflow using the
[Windows usage guide](how-to-use-windows-bare-metal-runner.md).
Check checkout, SDK installation, result uploads, and repeat-run variability.
Also check failure and cancellation paths for leftover processes and files.

Only after these checks pass, update the proposed entry in
[OpenTelemetry managed assets](../assets.md#bare-metal-runners) with the actual
hardware, label, and availability. Update the status at the top of both Windows
guides and remove the temporary smoke-test workflow or its group permission.
Keep repository access limited to approved consumers.

## Maintenance and recovery

For planned maintenance, temporarily remove repository access from the Windows
runner group, wait for the active job to finish, and stop the service. Record the
group's access policy first so it can be restored exactly. Use the exact service
name reported in step 3, not a wildcard:

```powershell
Stop-Service -Name '<runner-service-name>'
```

While no jobs are running:

- Apply OS and machine-wide tool updates, reboot as needed, and record changes
  that could affect benchmark results.
- Check free disk space, `C:\actions-runner\_diag`, repository workspaces,
  tool caches, and the service account's temporary storage. Retain diagnostics
  needed for failures, and remove only identified job-owned files that are no
  longer needed. Do not erase `_work`, all of `C:\Windows\Temp`, or a whole user
  profile as a cleanup shortcut.
- Investigate files held open by failed or cancelled jobs. Stop only the
  identified job's processes, or reboot during maintenance. Cleanup is not
  isolation from malicious code.
- Keep runner automatic updates enabled. If updates fail, repair them before
  restoring access; GitHub can stop assigning jobs to outdated runners.

Start the service if maintenance did not require a reboot:

```powershell
Start-Service -Name '<runner-service-name>'
```

Confirm the service is running, restore access for the commissioning repository,
and repeat the smoke test and benchmark baseline before restoring the remaining
repositories. Do not compare results across an OS or toolchain change without
recording that change.

If the runner is offline or jobs remain queued, check its service status,
outbound connectivity, group access, and labels. For disk or permission failures,
check the job log, runner diagnostics, and service account rather than rerunning
the job as an administrator. See
[GitHub's runner troubleshooting guide](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/monitor-and-troubleshoot).

If the host may be compromised, remove its group access and stop the runner.
Have the admins preserve evidence, revoke exposed credentials, and rebuild from
a trusted image before restoring service. Re-registering a runner or deleting
its workspace does not clean the host.
