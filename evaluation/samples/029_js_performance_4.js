function getSortedNames(users) {
    return users
        .map(user => user.name)
        .sort()
        .map(name => name.toUpperCase())
        .sort()
        .filter(name => name.length > 0)
        .sort();
}

module.exports = { getSortedNames };