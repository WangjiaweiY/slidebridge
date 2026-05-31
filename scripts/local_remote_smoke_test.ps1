param(
    [string]$RemoteSlide = "user@server:/data/slides/case.svs",
    [string]$RemoteRunner = "conda run -n slidebridge slidebridge",
    [int]$LocalPort = 7860,
    [int]$RemotePort = 7860
)

slidebridge remote-check $RemoteSlide --remote-runner $RemoteRunner
slidebridge remote-inspect $RemoteSlide --remote-runner $RemoteRunner
slidebridge remote-view $RemoteSlide --remote-runner $RemoteRunner --local-port $LocalPort --remote-port $RemotePort --open-browser
