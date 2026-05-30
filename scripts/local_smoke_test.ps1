param(
    [string]$SlidePath = "C:\path\to\your\slide.svs"
)

slidebridge env
slidebridge readers
slidebridge inspect $SlidePath --json
slidebridge thumbnail $SlidePath --out outputs\thumbnail.jpg --max-size 2048
slidebridge doctor $SlidePath --out outputs\qc_report.html --json-out outputs\qc_report.json
slidebridge sample-patches $SlidePath --out outputs\coords.csv --patch-size 512 --count 100

