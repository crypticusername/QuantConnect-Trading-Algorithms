# QC-Oracle: QuantConnect Specialized Assistant

## Project Overview

QC-Oracle is a specialized QuantConnect assistant that provides intelligent algorithm analysis, debugging, and generation capabilities through an n8n workflow connected to Windsurf Cascade via an MCP server.

## System Architecture

### 1. Data Processing Layer

**Vector Database: Supabase with pgvector**
- Store embeddings of QuantConnect documentation and code examples
- Enable semantic search across 20,000+ documentation files
- Maintain metadata for filtering (asset class, component type, etc.)

**Document Processing Pipeline**
- Repository scanning and file extraction
- Document chunking with context preservation
- Embedding generation via OpenAI API
- Metadata tagging and indexing

### 2. n8n Workflow Layer

**Core Workflows**
1. **Document Ingestion Workflow**
   - Process documentation repositories in batches
   - Generate and store embeddings
   - Update metadata index

2. **Query Processing Workflow**
   - Accept user queries with mode selection
   - Retrieve relevant documentation based on query
   - Construct context-aware prompts
   - Route to appropriate LLM via OpenRouter
   - Format and return responses

3. **Mode-Specific Workflows**
   - Algorithm Analysis: Code review and parameter verification
   - Algorithm Generation: Strategy-to-implementation scaffolding
   - Backtest Debugging: Log analysis with documentation-backed solutions

### 3. MCP Server Layer

**Server Implementation**
- Node.js Express server implementing MCP protocol
- Wrapper around n8n workflows via API
- Authentication and rate limiting
- Error handling and logging

**MCP Tools**
- `qc_analyze_algorithm`: Deep code review and parameter verification
- `qc_generate_algorithm`: Strategy-to-implementation scaffolding
- `qc_debug_backtest`: Log analysis with documentation-backed solutions

## Implementation Plan

### Phase 1: Data Infrastructure (3 days)
1. Set up Supabase instance with pgvector extension
2. Create document processing pipeline
3. Process and index QC-Doc-Repos content
4. Implement basic semantic search

### Phase 2: n8n Workflow Development (4 days)
1. Create core query processing workflow
2. Develop mode-specific prompt templates
3. Implement OpenRouter integration
4. Build response formatting and error handling

### Phase 3: MCP Server Development (3 days)
1. Create Node.js MCP server
2. Implement n8n workflow API integration
3. Define MCP tool interfaces
4. Add authentication and rate limiting

### Phase 4: Testing and Refinement (2 days)
1. Test with various algorithm scenarios
2. Refine prompt templates based on results
3. Optimize vector search parameters
4. Implement feedback loop for continuous improvement

## Technical Requirements

### Infrastructure
- Supabase instance with pgvector extension
- n8n self-hosted instance
- Node.js hosting environment for MCP server
- OpenRouter API account

### API Integrations
- OpenAI API (for embeddings)
- OpenRouter API (for LLM access)
- Supabase API
- n8n REST API

### Data Sources
- QuantConnect Documentation repository
- Lean repository
- Lean.Brokerages.InteractiveBrokers repository
- lean-cli repository
- Additional QuantConnect forum content (optional)

## Specialized Modes

### Algorithm Analysis Mode
- Parameter usage verification
- Code structure analysis
- Risk management assessment
- Performance optimization suggestions
- Compliance with QuantConnect best practices

### Algorithm Generation Mode
- Strategy-to-implementation scaffolding
- Parameter configuration guidance
- Asset class-specific templates
- Risk management integration
- Backtest configuration

### Backtest Debugging Mode
- Log analysis and error identification
- Documentation-backed solutions
- Common issue pattern recognition
- Performance bottleneck identification
- Implementation suggestions

## Integration with Windsurf Cascade

1. Install QC-Oracle MCP server using mcp-installer
2. Register MCP tools with Cascade
3. Access specialized tools during algorithm development
4. Maintain context between interactions

## Success Metrics

1. Accuracy of algorithm analysis compared to manual review
2. Quality of generated algorithm implementations
3. Success rate of debugging suggestions
4. Response time and resource efficiency
5. User satisfaction and workflow improvement

## Future Enhancements

1. Continuous learning from user interactions
2. Integration with QuantConnect Cloud API
3. Custom algorithm templates based on user preferences
4. Performance optimization analysis
5. Multi-algorithm portfolio analysis
