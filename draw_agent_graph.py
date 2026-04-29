from app.services.agent_service import AgentService

def main():
    agent_service = AgentService()
    graph = agent_service.agent.graph

    graph.get_graph().draw_mermaid_png(
        output_file_path="agent_graph.png"
    )

if __name__ == "__main__":
    main()