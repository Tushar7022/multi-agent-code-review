const express = require("express");
const fs = require("fs");
const path = require("path");
const app = express();

app.get("/read", (req, res) => {
    const filename = req.query.filename;
    const filePath = path.join(__dirname, "files", filename);
    const data = fs.readFileSync(filePath, "utf8");
    res.send(data);
});

app.listen(3000);