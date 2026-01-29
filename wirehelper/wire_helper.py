import math

class wire:
    def __init__(self, length, diameter, resistivity):
        self.length = length          # Length of the wire in meters
        self.diameter = diameter      # Diameter of the wire in meters
        self.resistivity = resistivity # Resistivity of the material in ohm-meters

    def cross_sectional_area(self):
        """Calculate the cross-sectional area of the wire."""
        radius = self.diameter / 2
        return math.pi * (radius ** 2)

    def resistance(self):
        """Calculate the resistance of the wire."""
        area = self.cross_sectional_area()
        return (self.resistivity * self.length) / area
    
    @staticmethod
    def awg_to_diameter_mm(awg):
        """
        Convert AWG (American Wire Gauge) to wire diameter in millimeters.
        Valid for AWG 18 to 40.
        
        Args:
            awg: Wire gauge (18-40)
        
        Returns:
            Wire diameter in millimeters
        """
        # AWG to diameter mapping (in mm)
        awg_table = {
            18: 1.024, 19: 0.912, 20: 0.812, 21: 0.723, 22: 0.644,
            23: 0.573, 24: 0.511, 25: 0.455, 26: 0.405, 27: 0.361,
            28: 0.321, 29: 0.286, 30: 0.255, 31: 0.227, 32: 0.202,
            33: 0.180, 34: 0.160, 35: 0.143, 36: 0.127, 37: 0.113,
            38: 0.101, 39: 0.090, 40: 0.080
        }
        
        if awg not in awg_table:
            raise ValueError(f"AWG must be between 18 and 40. Got: {awg}")
        
        return awg_table[awg]

class wire_windings:
    def __init__(self, wire, turns, spacing):
        self.wire = wire            # Instance of wire class
        self.turns = turns          # Number of turns in the winding
        self.spacing = spacing      # Spacing between turns in meters

    def total_length(self):
        """Calculate the total length of wire used in the windings."""
        return self.turns * (self.wire.length + self.spacing)

    def total_resistance(self):
        """Calculate the total resistance of the wire windings."""
        total_length = self.total_length()
        area = self.wire.cross_sectional_area()
        return (self.wire.resistivity * total_length) / area
    
    def calculate_spindle_length(self, awg):
        """
        Calculate the spindle length needed for the turns and given wire AWG.
        
        Args:
            awg: Wire gauge (18-40)
        
        Returns:
            Spindle length in millimeters
        """
        wire_diameter_mm = wire.awg_to_diameter_mm(awg)
        spindle_length = self.turns * wire_diameter_mm
        return spindle_length

def calculate_first_layer_turns(awg, spindle_length_mm):
    """
    Calculate the number of turns that fit in the first layer based on AWG and spindle length.
    
    Args:
        awg: Wire gauge (18-40)
        spindle_length_mm: Length of the spindle in millimeters
    
    Returns:
        Number of turns that fit in the first layer (integer)
    """
    wire_diameter_mm = wire.awg_to_diameter_mm(awg)
    turns = int(spindle_length_mm / wire_diameter_mm)
    return turns

def calculate_winding_height(awg, spindle_length_mm, desired_turns):
    """
    Calculate the height of orthocyclic windings for a given AWG, spindle length, and total turns.
    
    Args:
        awg: Wire gauge (18-40)
        spindle_length_mm: Length of the spindle in millimeters
        desired_turns: Total number of turns needed
    
    Returns:
        Height of the windings in millimeters
    """
    # Get wire diameter
    wire_diameter_mm = wire.awg_to_diameter_mm(awg)
    
    # Calculate how many turns fit in the first layer
    first_layer_turns = calculate_first_layer_turns(awg, spindle_length_mm)
    
    # Create orthocyclic winding calculator
    winding = orthocyclic(first_layer_turns)
    
    # Calculate how many layers are needed
    layers_needed = winding.layers_needed(desired_turns)
    
    # Height = number of layers * wire diameter
    height_mm = layers_needed * wire_diameter_mm
    
    return height_mm

class orthocyclic:
    def __init__(self, base_turns):
        """
        Initialize orthocyclic winding calculator.
        
        Args:
            base_turns: Number of turns in the first (odd) layer
        """
        self.base_turns = base_turns
    
    def turns_per_layer(self, layer_number):
        """
        Calculate the number of turns for a specific layer in orthocyclic winding.
        Even numbered layers have one less turn than odd numbered layers.
        
        Args:
            layer_number: Layer number (1-indexed)
        
        Returns:
            Number of turns in the specified layer
        """
        if layer_number % 2 == 0:  # Even layer
            return self.base_turns - 1
        else:  # Odd layer
            return self.base_turns
    
    def total_turns(self, num_layers):
        """
        Calculate the total number of turns across all layers in orthocyclic winding.
        Even numbered layers have one less turn than odd numbered layers.
        
        Args:
            num_layers: Total number of layers
        
        Returns:
            Total number of turns across all layers
        """
        total = 0
        for layer in range(1, num_layers + 1):
            total += self.turns_per_layer(layer)
        return total
    
    def layer_breakdown(self, num_layers):
        """
        Generate a breakdown of turns for each layer in orthocyclic winding.
        Even numbered layers have one less turn than odd numbered layers.
        
        Args:
            num_layers: Total number of layers
        
        Returns:
            List of tuples (layer_number, turns_in_layer)
        """
        breakdown = []
        for layer in range(1, num_layers + 1):
            turns = self.turns_per_layer(layer)
            breakdown.append((layer, turns))
        return breakdown
    
    def layers_needed(self, desired_turns):
        """
        Calculate the number of layers needed to achieve a desired number of turns.
        
        Args:
            desired_turns: The total number of turns desired
        
        Returns:
            Number of layers needed to meet or exceed the desired turns
        """
        layer = 1
        accumulated_turns = 0
        
        while accumulated_turns < desired_turns:
            accumulated_turns += self.turns_per_layer(layer)
            if accumulated_turns >= desired_turns:
                return layer
            layer += 1
        
        return layer
    
# Example usage:
if __name__ == "__main__":
    copper_resistivity = 1.68e-8  # Ohm-meters for copper
    my_wire = wire(length=2.0, diameter=0.01, resistivity=copper_resistivity)
    
    print(f"Cross-sectional Area: {my_wire.cross_sectional_area():.6e} m^2")
    print(f"Resistance: {my_wire.resistance():.6e} Ohms")
    
    # Orthocyclic winding example
    print("\n--- Orthocyclic Winding Example ---")
    awg = 20
    spindle_length = 20  # mm
    num_layers = 5
    
    first_layer_turns = calculate_first_layer_turns(awg, spindle_length)
    print(f"AWG {awg} wire on {spindle_length}mm spindle:")
    print(f"First layer turns: {first_layer_turns}")
    
    # Create orthocyclic winding object
    winding = orthocyclic(first_layer_turns)
    
    total_turns = winding.total_turns(num_layers)
    print(f"Total turns ({num_layers} layers): {total_turns}")
    
    print("\nLayer breakdown:")
    for layer, turns in winding.layer_breakdown(num_layers):
        print(f"  Layer {layer}: {turns} turns")    
    # Calculate layers needed for a specific number of turns
    print("\n--- Layers Needed Example ---")
    awg_example = 20
    spindle_example = 12  # mm
    desired_turns = 300
    
    base_turns = calculate_first_layer_turns(awg_example, spindle_example)
    winding_example = orthocyclic(base_turns)
    
    layers_required = winding_example.layers_needed(desired_turns)
    actual_turns = winding_example.total_turns(layers_required)
    
    print(f"AWG {awg_example} wire on {spindle_example}mm spindle:")
    print(f"To achieve {desired_turns} turns, you need {layers_required} layers")
    print(f"This will give you {actual_turns} total turns")
    
    # Calculate winding height
    print("\n--- Winding Height Calculation Example ---")
    awg_height = 20
    spindle_height = 12  # mm
    turns_height = 203
    
    winding_height = calculate_winding_height(awg_height, spindle_height, turns_height)
    
    print(f"AWG {awg_height} wire on {spindle_height}mm spindle with {turns_height} turns:")
    print(f"Winding height: {winding_height:.2f}mm")
