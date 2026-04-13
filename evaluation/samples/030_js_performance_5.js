function countWordFrequencies(words) {
    const counts = {};

    for (let i = 0; i < words.length; i++) {
        const word = words[i];
        const currentCount = words.filter(w => w === word).length;
        counts[word] = currentCount;
    }

    return counts;
}

module.exports = { countWordFrequencies };