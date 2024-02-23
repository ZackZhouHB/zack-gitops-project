resource "aws_instance" "blog" {
  ami           = "ami-0df4b2961410d4cff"
  instance_type = "t2.micro"
}