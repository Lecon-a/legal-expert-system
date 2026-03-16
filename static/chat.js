// UPLOAD DOCUMENT
document.getElementById("uploadForm").addEventListener("submit", async function(e){

    e.preventDefault()

    const fileInput = document.getElementById("document")

    const formData = new FormData()
    formData.append("document", fileInput.files[0])

    document.getElementById("uploadStatus").innerText = "Uploading and indexing document..."

    const response = await fetch("/upload",{
        method:"POST",
        body:formData
    })

    const text = await response.text()

    document.getElementById("uploadStatus").innerText = text

})