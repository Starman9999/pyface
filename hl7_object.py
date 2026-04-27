import json
from typing import Dict, List, Any, Optional


class HL7Object:
    def __init__(self):
        self.raw_message = ""
        self.segments = {}

        # Comprehensive field definitions for PID (v2.5.1)
        # Structure: field_index -> {component_index: "attribute_suffix"}
        self._pid_components = {
            5: {  # Patient Name
                1: "last_name",
                2: "first_name",
                3: "middle_name",
                4: "suffix",
                5: "prefix",
                6: "degree",
                7: "name_type_code",
                8: "identifier_check_digit",
                9: "check_digit_scheme",
                10: "assigning_authority",
                11: "name_representation_code",
                12: "name_context",
                13: "name_validity_range",
                14: "name_order",
                15: "name_effort"
            },
            11: {  # Patient Address
                1: "street_address",
                2: "other_designation",
                3: "city",
                4: "state_or_province",
                5: "zip_or_postal_code",
                6: "country",
                7: "address_type",
                8: "other_geographic_designation",
                9: "county_parish_code",
                10: "census_tract",
                11: "address_representation_code",
                12: "address_usage_code",
                13: "address_priority_code",
                14: "effective_date",
                15: "expiration_date"
            },
            # Add other complex fields here as needed
        }

    def _parse_components(self, field_value: str, segment_name: str, field_index: int) -> Dict[str, str]:
        """
        Parses a field value into components based on the HL7 definition.
        Returns a dict of {component_name: value}
        """
        if not field_value:
            return {}

        # Split by component separator '^'
        # Note: In some HL7 versions, subcomponents use '&' or '\'
        # We'll stick to '^' for now as per standard v2.5
        components = field_value.split('^')

        result = {}

        # Check if we have specific definitions for this segment/field
        if segment_name == 'PID' and field_index in self._pid_components:
            comp_map = self._pid_components[field_index]
            for idx, value in enumerate(components):
                # HL7 components are 1-based
                comp_idx = idx + 1
                if comp_idx in comp_map:
                    attr_suffix = comp_map[comp_idx]
                    result[attr_suffix] = value.strip()
                else:
                    # Fallback for undefined components
                    result[f"component_{comp_idx}"] = value.strip()
        else:
            # No specific definition, just return the whole string or generic components
            if len(components) > 1:
                for idx, value in enumerate(components):
                    result[f"component_{idx + 1}"] = value.strip()
            else:
                result["raw"] = field_value.strip()

        return result

    def populate_from_segments(self, segments: List[str]):
        for segment_str in segments:
            if not segment_str.strip():
                continue

            fields = segment_str.split('|')
            segment_id = fields[0]

            # Process each field
            for i, field_value in enumerate(fields):
                if i == 0:
                    continue  # Skip Segment ID

                field_index = i

                # 1. Parse Components first
                component_data = self._parse_components(field_value, segment_id, field_index)

                # 2. Assign attributes
                if component_data:
                    # If we have components, assign them individually
                    for comp_name, comp_val in component_data.items():
                        # Format: self.pid_5_last_name
                        attr_name = f"{segment_id.lower()}_{field_index}_{comp_name}"
                        setattr(self, attr_name, comp_val)

                    # Also keep the raw field value for reference
                    raw_attr = f"{segment_id.lower()}_{field_index}_raw"
                    setattr(self, raw_attr, field_value)
                else:
                    # No components defined, just set the raw value
                    # Try to find a generic description if possible
                    desc = self._get_description(segment_id, field_index)
                    attr_name = f"{segment_id.lower()}_{field_index}_{desc}"
                    setattr(self, attr_name, field_value.strip())

    def _get_description(self, segment_name: str, field_index: int) -> str:
        # Simplified version for fallback
        # In a full implementation, you'd have a full map for all segments
        generic_names = {
            'MSH': {1: 'field_separator', 2: 'encoding_chars', 3: 'sending_app', 4: 'sending_fac',
                    5: 'receiving_app', 6: 'receiving_fac', 7: 'datetime', 8: 'security',
                    9: 'msg_type', 10: 'msg_control_id', 11: 'proc_id', 12: 'version'},
            'PID': {1: 'set_id', 2: 'ext_id', 3: 'int_id', 4: 'alt_id', 5: 'name', 6: 'mothers_maiden',
                    7: 'dob', 8: 'sex', 9: 'alias', 10: 'race', 11: 'address', 12: 'county',
                    13: 'phone_home', 14: 'phone_work', 15: 'language', 16: 'marital', 17: 'religion',
                    18: 'acct_num', 19: 'ssn', 20: 'drivers_license', 21: 'mothers_id', 22: 'citizenship',
                    23: 'ethnic', 24: 'birthplace', 25: 'multi_birth', 26: 'birth_order', 27: 'country',
                    28: 'admin_status', 29: 'patient_type', 30: 'insurance_acct', 31: 'int_id_sec',
                    32: 'int_id_tert', 33: 'nationality', 34: 'death_datetime', 35: 'death_indicator'}
        }

        if segment_name in generic_names and field_index in generic_names[segment_name]:
            return generic_names[segment_name][field_index]
        return f"field_{field_index}"


def parse_hl7_file(filepath: str) -> HL7Object:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Handle both \r and \n as separators
    raw_segments = re.split(r'[\r\n]+', content)
    segments = [s.strip() for s in raw_segments if s.strip()]

    hl7_obj = HL7Object()
    hl7_obj.raw_message = content
    hl7_obj.populate_from_segments(segments)

    return hl7_obj


def write_object_to_file(hl7_obj: HL7Object, output_path: str):
    obj_dict = {k: v for k, v in hl7_obj.__dict__.items() if not k.startswith('_')}
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(obj_dict, f, indent=2)
    print(f"Object written to {output_path}")


if __name__ == "__main__":
    import re

    input_file = "files/sample.txt"
    output_file = "parsed_with_components.json"

    try:
        hl7_data = parse_hl7_file(input_file)
        write_object_to_file(hl7_data, output_file)

        print("\n--- Component Parsing Results ---")
        # Check PID 5 (Patient Name) components
        if hasattr(hl7_data, 'pid_5_last_name'):
            print(f"Patient Name: {hl7_data.pid_5_last_name}, {hl7_data.pid_5_first_name}")
        else:
            print("PID 5 components not found (check raw value)")
            if hasattr(hl7_data, 'pid_5_raw'):
                print(f"Raw PID 5: {hl7_data.pid_5_raw}")

        # Check PID 11 (Address)
        if hasattr(hl7_data, 'pid_11_city'):
            print(f"City: {hl7_data.pid_11_city}")

    except Exception as e:
        print(f"Error: {e}")