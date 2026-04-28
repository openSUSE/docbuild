from docbuild.utils.flatten import flatten_dict


def test_flatten_dict_nested():
    """Test that flatten_dict correctly flattens nested dictionaries."""
    data = {"a": {"b": {"c": 1}}, "d": 2}
    result = dict(flatten_dict(data))
    assert result == {"a.b.c": 1, "d": 2}

def test_flatten_dict_empty():
    """Test that flatten_dict correctly handles an empty dictionary."""
    assert dict(flatten_dict({})) == {}
