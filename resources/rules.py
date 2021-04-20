CATEGORY_RULES = {
    'VU Employee': {
        'expires_in': 2,  # 1 <= expiration date - today <= X months
        'last_activity': 12,  # today - last activity date <= X months
        'expire_add': 12  # add X months to the existing expiration date)
    },
    'VUmc Employee': {
        'expires_in': 2,
        'last_activity': 12,
        'expire_add': 12
    },
    'VU Student': {
        'expires_in': 2,
        'last_activity': 12,
        'expire_add': 12
    },
    'ILL': {
        'expires_in': 3,
        'last_activity': 12,
        'expire_add': 12
    }
}