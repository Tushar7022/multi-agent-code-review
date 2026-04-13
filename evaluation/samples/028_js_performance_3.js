function buildMessage(items) {
    let message = "";

    for (let i = 0; i < items.length; i++) {
        message = message + items[i] + ",";
    }

    return message;
}

module.exports = { buildMessage };