import ast
import os
import networkx as nx
import matplotlib.pyplot as plt
import re
from pathlib import Path

def extract_imports_from_file(file_path):
    """
    Extract all imports from a Python file using AST parsing.
    
    Parameters:
    file_path (str): Path to the Python file
    
    Returns:
    dict: Dictionary with 'imports', 'from_imports', and 'local_imports'
    """
    imports = {
        'imports': [],           # import module
        'from_imports': [],      # from module import item
        'local_imports': []      # imports that are local Python files
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports['imports'].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports['from_imports'].append(node.module)
                    
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
    
    return imports

def find_local_imports(imports_dict, python_files_in_folder):
    """
    Identify which imports are local Python files in the same folder.
    
    Parameters:
    imports_dict (dict): Dictionary of imports from extract_imports_from_file
    python_files_in_folder (set): Set of Python file names (without .py extension)
    
    Returns:
    list: List of local imports
    """
    local_imports = []
    
    # Check all imports
    all_imports = imports_dict['imports'] + imports_dict['from_imports']
    
    for imp in all_imports:
        # Remove any sub-module references (e.g., 'package.module' -> 'package')
        base_module = imp.split('.')[0]
        
        if base_module in python_files_in_folder:
            local_imports.append(base_module)
    
    return list(set(local_imports))  # Remove duplicates

def analyze_python_dependencies(folder_path):
    """
    Analyze dependencies among Python files in a folder.
    
    Parameters:
    folder_path (str): Path to the folder containing Python files
    
    Returns:
    dict: Dictionary mapping each file to its dependencies
    """
    folder_path = Path(folder_path)
    
    # Find all Python files in the folder
    python_files = list(folder_path.glob("*.py"))
    
    if not python_files:
        print(f"No Python files found in {folder_path}")
        return {}
    
    print(f"Found {len(python_files)} Python files")
    
    # Create a set of Python file names (without extension) for quick lookup
    python_file_names = {f.stem for f in python_files}
    
    dependencies = {}
    
    for py_file in python_files:
        file_name = py_file.stem
        print(f"Analyzing {file_name}.py...")
        
        # Extract imports
        imports = extract_imports_from_file(py_file)
        
        # Find local dependencies
        local_deps = find_local_imports(imports, python_file_names)
        
        dependencies[file_name] = {
            'local_dependencies': local_deps,
            'all_imports': imports['imports'] + imports['from_imports'],
            'external_dependencies': [imp for imp in imports['imports'] + imports['from_imports'] 
                                    if imp.split('.')[0] not in python_file_names]
        }
        
        if local_deps:
            print(f"  -> Depends on: {', '.join(local_deps)}")
        else:
            print(f"  -> No local dependencies")
    
    return dependencies

def create_dependency_graph(dependencies, save_path=None):
    """
    Create and display a network graph of dependencies.
    
    Parameters:
    dependencies (dict): Dependencies dictionary from analyze_python_dependencies
    save_path (str): Optional path to save the graph image
    """
    # Create directed graph
    G = nx.DiGraph()
    
    # Add all files as nodes
    for file_name in dependencies.keys():
        G.add_node(file_name)
    
    # Add edges for dependencies
    for file_name, deps in dependencies.items():
        for dep in deps['local_dependencies']:
            if dep in dependencies:  # Make sure the dependency file exists
                G.add_edge(file_name, dep)
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    
    # Use a layout algorithm
    if len(G.nodes()) > 10:
        pos = nx.spring_layout(G, k=2, iterations=50)
    else:
        pos = nx.circular_layout(G)
    
    # Draw the graph
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', 
                          node_size=3000, alpha=0.7)
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')
    nx.draw_networkx_edges(G, pos, edge_color='gray', 
                          arrows=True, arrowsize=20, alpha=0.6)
    
    plt.title("Python File Dependencies", fontsize=16, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Graph saved to {save_path}")
    
    plt.show()
    
    # Print statistics
    print(f"\nDependency Graph Statistics:")
    print(f"- Total files: {len(G.nodes())}")
    print(f"- Total dependencies: {len(G.edges())}")
    print(f"- Files with no dependencies: {len([n for n in G.nodes() if G.in_degree(n) == 0])}")
    print(f"- Files with no dependents: {len([n for n in G.nodes() if G.out_degree(n) == 0])}")

def generate_dependency_report(dependencies, output_file=None):
    """
    Generate a detailed text report of dependencies.
    
    Parameters:
    dependencies (dict): Dependencies dictionary from analyze_python_dependencies
    output_file (str): Optional file path to save the report
    """
    report = "Python File Dependency Report\n"
    report += "=" * 40 + "\n\n"
    
    for file_name, deps in dependencies.items():
        report += f"File: {file_name}.py\n"
        report += "-" * (len(file_name) + 10) + "\n"
        
        if deps['local_dependencies']:
            report += f"Local Dependencies: {', '.join(deps['local_dependencies'])}\n"
        else:
            report += "Local Dependencies: None\n"
        
        if deps['external_dependencies']:
            ext_deps = deps['external_dependencies'][:10]  # Limit to first 10
            report += f"External Dependencies: {', '.join(ext_deps)}"
            if len(deps['external_dependencies']) > 10:
                report += f" (and {len(deps['external_dependencies']) - 10} more)"
            report += "\n"
        else:
            report += "External Dependencies: None\n"
        
        report += "\n"
    
    print(report)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(report)
        print(f"Report saved to {output_file}")

def main():
    """
    Main function to analyze dependencies in the current folder.
    """
    # Analyze current folder (change this path as needed)
    folder_path = "."  # Current directory
    
    print(f"Analyzing Python dependencies in: {os.path.abspath(folder_path)}")
    print("=" * 60)
    
    # Analyze dependencies
    dependencies = analyze_python_dependencies(folder_path)
    
    if not dependencies:
        return
    
    print("\n" + "=" * 60)
    
    # Create and display the graph
    create_dependency_graph(dependencies, save_path="dependency_graph.png")
    
    # Generate detailed report
    generate_dependency_report(dependencies, output_file="dependency_report.txt")

if __name__ == "__main__":
    # Install required packages if not already installed
    try:
        import networkx as nx
        import matplotlib.pyplot as plt
    except ImportError:
        print("Required packages not found. Please install them with:")
        print("pip install networkx matplotlib")
        exit(1)
    
    main()