param(
    [string]$SlidePath = "C:\path\to\your\slide.svs",
    [string]$AnnotationPath = ""
)

slidebridge env
slidebridge readers
slidebridge inspect $SlidePath --json
slidebridge thumbnail $SlidePath --out outputs\thumbnail.jpg --max-size 2048
slidebridge doctor $SlidePath --out outputs\qc_report.html --json-out outputs\qc_report.json
slidebridge sample-patches $SlidePath --out outputs\coords.csv --patch-size 512 --count 100

if ($AnnotationPath -ne "") {
    slidebridge inspect-annotations $AnnotationPath --slide $SlidePath
    slidebridge render-overlay $SlidePath --annotations $AnnotationPath --out outputs\annotation_overlay.png
    slidebridge view $SlidePath --annotations $AnnotationPath --port 7860 --open-browser
}
