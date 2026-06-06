class ValidationError(ValueError):
    """Exception raised when API validation fails."""
    pass

def validate_string(val, field_name="value", min_length=1, allow_none=False):
    if val is None:
        if allow_none:
            return None
        raise ValidationError(f"Missing required field '{field_name}'")
    if not isinstance(val, str):
        raise ValidationError(f"'{field_name}' must be a string")
    val_stripped = val.strip()
    if len(val_stripped) < min_length:
        raise ValidationError(f"'{field_name}' must be at least {min_length} character(s) long")
    return val_stripped

def validate_float(val, field_name="value", min_val=0.0, max_val=None, allow_none=False):
    if val is None:
        if allow_none:
            return None
        raise ValidationError(f"Missing required field '{field_name}'")
    
    if isinstance(val, bool):
        raise ValidationError(f"'{field_name}' must be a valid float, not boolean")
        
    try:
        float_val = float(val)
    except (ValueError, TypeError):
        raise ValidationError(f"'{field_name}' must be a valid float")
        
    if min_val is not None and float_val < min_val:
        raise ValidationError(f"'{field_name}' cannot be less than {min_val}")
    if max_val is not None and float_val > max_val:
        raise ValidationError(f"'{field_name}' cannot be greater than {max_val}")
        
    return float_val

def validate_int(val, field_name="value", min_val=0, max_val=None, allow_none=False):
    if val is None:
        if allow_none:
            return None
        raise ValidationError(f"Missing required field '{field_name}'")
        
    if isinstance(val, bool):
        raise ValidationError(f"'{field_name}' must be a valid integer, not boolean")
        
    try:
        float_val = float(val)
        if not float_val.is_integer():
            raise ValueError()
        int_val = int(float_val)
    except (ValueError, TypeError):
        raise ValidationError(f"'{field_name}' must be a valid integer")
        
    if min_val is not None and int_val < min_val:
        raise ValidationError(f"'{field_name}' cannot be less than {min_val}")
    if max_val is not None and int_val > max_val:
        raise ValidationError(f"'{field_name}' cannot be greater than {max_val}")
        
    return int_val
