import math

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

def wire_resistance(length, awg, resistivity=1.72e-8):
    """
    Calculate the resistance of a wire.
    
    Args:
        length: Length of the wire in meters
        awg: Wire gauge (18-40)
        resistivity: Resistivity of the material in ohm-meters (default: enamel coated copper at 20°C)
    
    Returns:
        Resistance in Ohms
    """
    # Get wire diameter in mm and convert to meters
    diameter_mm = awg_to_diameter_mm(awg)
    diameter = diameter_mm / 1000.0
    
    # Calculate cross-sectional area
    radius = diameter / 2
    area = math.pi * (radius ** 2)
    
    # Calculate resistance
    return (resistivity * length) / area

def calculate_first_layer_turns(awg, spool_length_mm):
    """
    Calculate the number of turns that fit in the first layer based on AWG and spool length.
    
    Args:
        awg: Wire gauge (18-40)
        spool_length_mm: Length of the spool in millimeters
    
    Returns:
        Number of turns that fit in the first layer (integer)
    """
    wire_diameter_mm = awg_to_diameter_mm(awg)
    turns = int(spool_length_mm / wire_diameter_mm)
    return turns

def calculate_spool_length(awg, first_layer_turns):
    """
    Calculate the spool length needed for the first layer of turns and wire AWG.
    
    Args:
        awg: Wire gauge (18-40)
        first_layer_turns: Number of turns in the first layer
    
    Returns:
        Spool length in millimeters
    """
    wire_diameter_mm = awg_to_diameter_mm(awg)
    spool_length = first_layer_turns * wire_diameter_mm
    return spool_length

def calculate_winding_height(awg, spool_length_mm, desired_turns, drum_diameter_mm=0):
    """
    Calculate the height of orthocyclic windings for a given AWG, spool length, and total turns.
    
    Args:
        awg: Wire gauge (18-40)
        spool_length_mm: Length of the spool in millimeters
        desired_turns: Total number of turns needed
        drum_diameter_mm: Diameter of the drum/spool in millimeters (optional)
    
    Returns:
        Height of the windings in millimeters
    """
    # Create orthocyclic winding calculator
    winding = orthocyclic(spool_length_mm, awg, desired_turns, drum_diameter_mm)
    
    # Height = number of layers * wire diameter
    height_mm = winding.layers_needed_count * winding.wire_diameter_mm
    
    return height_mm

class orthocyclic:
    def __init__(self, spool_length_mm, awg, desired_turns, drum_diameter_mm=0.0):
        """
        Initialize orthocyclic winding calculator.
        
        Args:
            spool_length_mm: Length of the spool in millimeters
            awg: Wire gauge (18-40)
            desired_turns: Total number of turns needed
            drum_diameter_mm: Diameter of the spool drum in millimeters (optional, float)
        """
        self.spool_length_mm = float(spool_length_mm)
        self.awg = awg
        self.desired_turns = desired_turns
        self.drum_diameter_mm = float(drum_diameter_mm)
        # Calculate wire diameter internally from AWG
        self.wire_diameter_mm = awg_to_diameter_mm(awg)
        # Calculate base_turns internally from spool length and wire diameter
        self.base_turns = int(spool_length_mm / self.wire_diameter_mm)
        # Calculate layers needed internally
        self.layers_needed_count = self._calculate_layers_needed()
    
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
    
    def total_turns(self, num_layers=None):
        """
        Calculate the total number of turns across all layers in orthocyclic winding.
        Even numbered layers have one less turn than odd numbered layers.
        If num_layers is not provided, uses the calculated layers_needed_count.
        
        Args:
            num_layers: Total number of layers (optional, uses self.layers_needed_count if not provided)
        
        Returns:
            Total number of turns across all layers
        """
        if num_layers is None:
            num_layers = self.layers_needed_count
            
        total = 0
        for layer in range(1, num_layers + 1):
            total += self.turns_per_layer(layer)
        return total
    
    def layers_needed(self, desired_turns=None):
        """
        Calculate the number of layers needed to achieve a desired number of turns.
        If desired_turns is not provided, uses the value from initialization.
        
        Args:
            desired_turns: The total number of turns desired (optional, uses self.desired_turns if not provided)
        
        Returns:
            Number of layers needed to meet or exceed the desired turns
        """
        if desired_turns is None:
            desired_turns = self.desired_turns
        return self._calculate_layers_needed(desired_turns)
    
    def _calculate_layers_needed(self, desired_turns=None):
        """
        Internal method to calculate the number of layers needed.
        
        Args:
            desired_turns: The total number of turns desired (optional, uses self.desired_turns if not provided)
        
        Returns:
            Number of layers needed to meet or exceed the desired turns
        """
        if desired_turns is None:
            desired_turns = self.desired_turns
            
        layer = 1
        accumulated_turns = 0
        
        while accumulated_turns < desired_turns:
            accumulated_turns += self.turns_per_layer(layer)
            if accumulated_turns >= desired_turns:
                return layer
            layer += 1
        
        return layer
    
    def total_wire_length(self, num_layers=None):
        """
        Calculate the total length of wire needed for all layers.
        If num_layers is not provided, uses the calculated layers_needed_count.
        
        Args:
            num_layers: Total number of layers (optional, uses self.layers_needed_count if not provided)
        
        Returns:
            Total wire length in millimeters
        """
        if num_layers is None:
            num_layers = self.layers_needed_count
            
        if self.drum_diameter_mm == 0 or self.wire_diameter_mm == 0:
            return 0
        total_length = 0
        for layer in range(1, num_layers + 1):
            # Each layer adds 2 wire diameters to the overall diameter
            diameter = self.drum_diameter_mm + 2 * (layer - 1) * self.wire_diameter_mm
            circumference = math.pi * diameter
            turns = self.turns_per_layer(layer)
            total_length += turns * circumference
        return total_length
    
# Example usage:
if __name__ == "__main__":
    # Wire resistance example
    wire_length = 2.0  # meters
    wire_awg = 20
    copper_resistivity = 1.72e-8  # Ohm-meters for enamel coated copper magnet wire at 20°C
    
    resistance = wire_resistance(wire_length, wire_awg, copper_resistivity)
    print(f"Resistance: {resistance:.6e} Ohms")
    
    # Orthocyclic winding example
    print("\n--- Orthocyclic Winding Example ---")
    awg = 20
    spool_length = 12  # mm
    drum_diameter = 10  # mm
    num_layers = 15
    
    wire_diameter = awg_to_diameter_mm(awg)
    first_layer_turns = calculate_first_layer_turns(awg, spool_length)
    print(f"AWG {awg} wire on {spool_length}mm spool with {drum_diameter}mm drum:")
    print(f"Wire diameter: {wire_diameter:.3f}mm")
    print(f"First layer turns: {first_layer_turns}")
    
    # Create orthocyclic winding object
    winding = orthocyclic(spool_length, awg, num_layers * first_layer_turns, drum_diameter)
    
    total_turns = winding.total_turns()
    total_wire = winding.total_wire_length()
    print(f"Total turns ({num_layers} layers): {total_turns}")
    print(f"Total wire length needed: {total_wire:.2f}mm ({total_wire/1000:.3f}m)")
    
    # Calculate layers needed for a specific number of turns
    print("\n--- Layers Needed Example ---")
    awg_example = 20
    spool_example = 12  # mm
    drum_example = 10  # mm
    desired_turns = 200
    
    wire_diameter_ex = awg_to_diameter_mm(awg_example)
    base_turns = calculate_first_layer_turns(awg_example, spool_example)
    winding_example = orthocyclic(spool_example, awg_example, desired_turns, drum_example)
    
    layers_required = winding_example.layers_needed_count
    actual_turns = winding_example.total_turns()
    wire_length_needed = winding_example.total_wire_length()
    
    print(f"AWG {awg_example} wire on {spool_example}mm spool with {drum_example}mm drum:")
    print(f"To achieve {desired_turns} turns, you need {layers_required} layers")
    print(f"This will give you {actual_turns} total turns")
    print(f"Total wire length needed: {wire_length_needed:.2f}mm ({wire_length_needed/1000:.3f}m)")
    
    # Calculate winding height
    print("\n--- Winding Height Calculation Example ---")
    awg_height = 20
    spool_height = 12  # mm
    drum_height = 10  # mm
    turns_height = 100
    
    winding_height = calculate_winding_height(awg_height, spool_height, turns_height, drum_height)
    
    print(f"AWG {awg_height} wire on {spool_height}mm spool with {drum_height}mm drum and {turns_height} turns:")
    print(f"Winding height: {winding_height:.2f}mm")
