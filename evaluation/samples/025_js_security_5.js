const express = require("express");
const fetch = require("node-fetch");
const app = express();

app.get("/fetch-data", async (req, res) => {
    const targetUrl = req.query.url;
    const response = await fetch(targetUrl);
    const data = await response.text();
    res.send(data);
});

app.listen(3000);