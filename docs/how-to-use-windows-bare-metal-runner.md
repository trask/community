# How to use an Oracle Windows bare metal runner

The Windows runner is proposed, not yet available. The label below is reserved
for the planned setup; do not enable workflows targeting it until
[OpenTelemetry managed assets](../assets.md#bare-metal-runners) lists it as
available. Jobs without an online, eligible runner will remain queued and
eventually fail.

This is a shared, persistent Windows Server 2022 benchmark host. It is separate
from the Linux bare metal runner and the GitHub-hosted
`otel-windows-latest-8-cores` runner.
Admins should use the [Windows provisioning guide](how-to-provision-windows-bare-metal-runner.md).

## Request access

Open a community issue with:

- The repository that needs access.
- The benchmark workflow and why it needs dedicated Windows hardware.
- Its triggers, the source of code it executes, expected duration and frequency.
- Required SDKs, native build tools, profiling permissions, and cleanup behavior.

Admins grant access through the
**Oracle Cloud Windows bare metal benchmark runners** group.
Repository access can permit all workflows in that repository unless the group
also restricts workflows. A runner label routes jobs; it is not an access control.

Run only trusted code from approved refs, such as scheduled default-branch runs
or releases. Do not run untrusted pull-request code on this host, including
through `pull_request_target`, manually supplied refs, or downloaded binaries.
Manual approval does not reset the machine between jobs.
Keep job token permissions minimal and do not put publishing credentials or
other long-lived secrets on the host. Publish results from a separate
GitHub-hosted job when additional credentials are needed.

## Run directly on Windows

Use the label:

```yaml
runs-on: oracle-bare-metal-64cpu-1024gb-x86-64-windows-2022
```

Unlike the Linux runner, this runner does not support GitHub Actions
`container:`, service containers, or Docker container actions.
Use native Windows commands and Windows-compatible actions.
See [GitHub's self-hosted runner requirements](https://docs.github.com/en/actions/reference/runners/self-hosted-runners#requirements-for-self-hosted-runner-machines).

The host provides Git and PowerShell 7. Workflows must select their language
SDKs explicitly; do not assume the software available on `windows-latest`
is installed here. Pin SDK versions and dependencies. Ask admins to install
tools that require elevation rather than elevating the runner service or
changing machine-wide settings in a workflow.

### Example .NET benchmark workflow

This example assumes a repository with a `global.json` at its root and a
BenchmarkDotNet console project at `benchmarks\Benchmarks.csproj` that accepts
BenchmarkDotNet command-line arguments. Replace the project path and benchmark
filter with the repository's own values. Pin an exact SDK version in
`global.json`, with `rollForward` set to `disable` for a fixed SDK.

The manual trigger permits the default branch only. If runner-group workflow
restrictions are enabled, admins must also allow this workflow and ref.

```yaml
name: Windows benchmarks

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  benchmark:
    if: github.ref == format('refs/heads/{0}', github.event.repository.default_branch)
    runs-on: oracle-bare-metal-64cpu-1024gb-x86-64-windows-2022
    timeout-minutes: 120
    defaults:
      run:
        shell: pwsh
    env:
      TMP: ${{ runner.temp }}
      TEMP: ${{ runner.temp }}
      DOTNET_INSTALL_DIR: ${{ runner.temp }}\dotnet
      DOTNET_CLI_HOME: ${{ runner.temp }}\dotnet-home
      NUGET_PACKAGES: ${{ runner.temp }}\nuget
      NUGET_HTTP_CACHE_PATH: ${{ runner.temp }}\nuget-http
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: actions/setup-dotnet@a98b56852c35b8e3190ac28c8c2271da59106c68 # v6.0.0
        id: setup-dotnet
        with:
          global-json-file: global.json
      - name: Record environment
        run: |
          Get-CimInstance Win32_OperatingSystem |
              Select-Object Caption, Version, BuildNumber
          Get-CimInstance Win32_Processor |
              Select-Object Name, NumberOfCores, NumberOfLogicalProcessors
          dotnet --info
      - name: Run benchmarks
        run: |
          dotnet run --configuration Release --project benchmarks\Benchmarks.csproj -- `
              --filter '*' --artifacts "$env:RUNNER_TEMP\benchmark-results"
      - name: Upload results
        if: ${{ !cancelled() }}
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: windows-benchmark-results
          path: ${{ runner.temp }}\benchmark-results
          if-no-files-found: error
      - name: Stop build servers
        if: ${{ always() && steps.setup-dotnet.outcome == 'success' }}
        run: dotnet build-server shutdown
```

Installing the SDK under `runner.temp` avoids requiring write access to
`C:\Program Files\dotnet`. Other languages can follow the same pattern with
their setup action, pinned tool versions, and writable installation paths.

## Clean up after the job

Set `TMP` and `TEMP` to `${{ runner.temp }}` so tools use job temporary storage.
GitHub [empties this directory at the start and end of a job](https://docs.github.com/en/actions/reference/workflows-and-actions/variables),
but cannot remove files the service account lacks permission to delete.
Upload results before the job ends.

The runner does not reset the rest of the filesystem. Keep tool downloads,
temporary files, and disposable caches under `runner.temp` where possible.
For persistent caches, agree on their location and size limit with admins.
Clean repository build outputs with the project's own cleanup command.

If a workflow creates files outside `runner.temp` or starts a background process,
add an `if: always()` cleanup step for those exact resources. Track process IDs
and wait for child processes to exit so they cannot interfere with the next
benchmark. Do not delete entire shared temporary directories or kill processes
by executable name. Cleanup steps may not finish after a forced cancellation
or host failure; report leftovers to admins.

## Keep measurements comparable

There is one runner service on the dedicated Windows host, so GitHub queues
jobs instead of running multiple jobs on the machine at once.
Do not start parallel benchmark processes within a job. A workflow's
`concurrency` group is repository-scoped and cannot coordinate different
repositories.

Use warmup and repeated measurements, and keep Windows results separate from
Linux results. Record the commit, OS build, SDK and runtime versions, benchmark
configuration, and any CPU affinity or NUMA settings with each result set.
On this 128-logical-processor machine, verify the benchmark framework's Windows
processor-group behavior before interpreting scaling results.

Do not change the power plan, security software, OS configuration, or installed
machine-wide tools from a workflow. Coordinate unusually long runs, profiling
that needs elevated privileges, and suspected measurement noise with admins.
If the runner is offline, out of space, or leaving processes behind, open a
community issue with the workflow run link and relevant diagnostics, without
credentials or private host details.
